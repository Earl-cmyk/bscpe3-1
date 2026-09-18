from decimal import Decimal, InvalidOperation
from pathlib import Path

from .rich_text import rich_text_plain, sanitize_rich_text
from .schedule import parse_manila_date, parse_manila_datetime
from config import ALLOWED_DIFFICULTIES


MUTATING_TOOLS = {
    "create_deadline",
    "edit_deadline",
    "delete_deadline",
    "add_no_class_exception",
    "restore_class_exception",
    "create_note",
    "edit_note",
    "delete_note",
    "add_wallet",
    "add_payer",
    "record_transaction",
    "update_withdrawal_status",
    "post_announcement",
    "cast_poll_vote",
}


def _required(arguments, *names):
    missing = [name for name in names if not str(arguments.get(name, "")).strip()]
    if missing:
        raise ValueError(f"Missing required argument: {missing[0]}")


def _course(value):
    from config import ALLOWED_COURSES
    from .schedule import COURSE_SHORT

    text = str(value or "").strip()
    if text in ALLOWED_COURSES:
        return text
    for title, short in COURSE_SHORT.items():
        if text.casefold() in {title.casefold(), short.casefold()}:
            return short
    raise ValueError("Invalid course")


def _deadline(arguments):
    _required(arguments, "title", "course", "description", "datetime")
    difficulty = arguments.get("difficulty", "Medium")
    if difficulty not in ALLOWED_DIFFICULTIES:
        raise ValueError("Invalid difficulty")
    return {
        "title": str(arguments["title"]).strip(),
        "course": _course(arguments["course"]),
        "description": sanitize_rich_text(arguments["description"]),
        "deadline": parse_manila_datetime(arguments["datetime"]),
        "difficulty": difficulty,
    }


def _note(arguments):
    _required(arguments, "title", "course", "caption")
    caption = sanitize_rich_text(arguments["caption"])
    if not rich_text_plain(caption):
        raise ValueError("Caption is required")
    return {"title": str(arguments["title"]).strip(), "course": _course(arguments["course"]), "caption": caption, "attachments": []}


def validate_tool(tool_name, arguments):
    if tool_name not in MUTATING_TOOLS:
        raise ValueError("Unknown or read-only tool")
    arguments = dict(arguments or {})
    if tool_name == "create_deadline":
        return _deadline(arguments)
    if tool_name == "edit_deadline":
        _required(arguments, "deadline_id")
        values = {key: arguments[key] for key in ("title", "description", "difficulty") if key in arguments}
        if "course" in arguments:
            values["course"] = _course(arguments["course"])
        if "datetime" in arguments:
            values["deadline"] = parse_manila_datetime(arguments["datetime"])
        return {"deadline_id": int(arguments["deadline_id"]), "fields": values}
    if tool_name == "delete_deadline":
        _required(arguments, "deadline_id")
        return {"deadline_id": int(arguments["deadline_id"])}
    if tool_name == "add_no_class_exception":
        _required(arguments, "course", "date")
        return {"course": _course(arguments["course"]), "date": parse_manila_date(arguments["date"]).isoformat()}
    if tool_name == "restore_class_exception":
        if arguments.get("exception_id"):
            return {"exception_id": int(arguments["exception_id"])}
        _required(arguments, "course", "date")
        return {"course": _course(arguments["course"]), "date": parse_manila_date(arguments["date"]).isoformat()}
    if tool_name == "create_note":
        return _note(arguments)
    if tool_name == "edit_note":
        _required(arguments, "note_id")
        values = {key: arguments[key] for key in ("title", "caption") if key in arguments}
        if "caption" in values:
            values["caption"] = sanitize_rich_text(values["caption"])
        if "course" in arguments:
            values["course"] = _course(arguments["course"])
        return {"note_id": int(arguments["note_id"]), "fields": values}
    if tool_name == "delete_note":
        _required(arguments, "note_id")
        return {"note_id": int(arguments["note_id"])}
    if tool_name == "add_wallet":
        _required(arguments, "wallet_name")
        result = {"name": str(arguments["wallet_name"]).strip()}
        if arguments.get("course"):
            result["course"] = _course(arguments["course"])
        return result
    if tool_name == "add_payer":
        _required(arguments, "payer_name")
        result = {"name": str(arguments["payer_name"]).strip()}
        if arguments.get("wallet_id"):
            result["wallet_id"] = int(arguments["wallet_id"])
        return result
    if tool_name == "record_transaction":
        _required(arguments, "type", "amount", "reason")
        if arguments["type"] not in {"deposit", "withdraw"}:
            raise ValueError("Transaction type must be deposit or withdraw")
        try:
            amount = Decimal(str(arguments["amount"]))
        except (InvalidOperation, ValueError):
            raise ValueError("Amount must be a valid number")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        result = {"type": arguments["type"], "amount": float(amount.quantize(Decimal("0.01"))), "reason": sanitize_rich_text(arguments["reason"])}
        if arguments.get("wallet_id"):
            result["wallet_id"] = int(arguments["wallet_id"])
        elif arguments.get("course"):
            result["course"] = _course(arguments["course"])
        else:
            raise ValueError("Wallet or course is required")
        if arguments.get("payer_id"):
            result["contributor_id"] = int(arguments["payer_id"])
        return result
    if tool_name == "update_withdrawal_status":
        _required(arguments, "transaction_id", "status")
        if arguments["status"] not in {"pending", "spent", "cancelled"}:
            raise ValueError("Invalid withdrawal status")
        return {"transaction_id": int(arguments["transaction_id"]), "status": arguments["status"]}
    if tool_name == "post_announcement":
        _required(arguments, "title", "message")
        choices = list(dict.fromkeys(str(choice).strip() for choice in arguments.get("poll_choices", []) if str(choice).strip()))
        if choices and len(choices) < 2:
            raise ValueError("A poll needs at least two choices")
        return {"title": str(arguments["title"]).strip(), "body": sanitize_rich_text(arguments["message"]), "link_url": arguments.get("link"), "options": choices}
    if tool_name == "cast_poll_vote":
        _required(arguments, "announcement_id", "choice_id", "school_id")
        return {"announcement_id": int(arguments["announcement_id"]), "option_id": int(arguments["choice_id"]), "school_id": str(arguments["school_id"]).strip()}
    raise ValueError("Unknown tool")


def dispatch_tool(database_path, tool_name, arguments):
    from ..models import (
        add_announcement, add_budget_entry, add_contributor, add_no_class_exception, add_note,
        add_poll_vote, add_task, add_wallet, delete_no_class_exception, delete_note, delete_task,
        get_note, get_task, get_wallet, list_wallets, update_budget_entry, update_note, update_task,
    )

    if tool_name == "create_deadline":
        return add_task(database_path, arguments)
    if tool_name == "edit_deadline":
        if not get_task(database_path, arguments["deadline_id"]):
            raise ValueError("Deadline not found")
        return update_task(database_path, arguments["deadline_id"], arguments["fields"])
    if tool_name == "delete_deadline":
        if not get_task(database_path, arguments["deadline_id"]):
            raise ValueError("Deadline not found")
        delete_task(database_path, arguments["deadline_id"])
        return {"id": arguments["deadline_id"], "deleted": True}
    if tool_name == "add_no_class_exception":
        return add_no_class_exception(database_path, arguments["date"], arguments["course"])
    if tool_name == "restore_class_exception":
        if arguments.get("exception_id"):
            return delete_no_class_exception(database_path, arguments["exception_id"])
        from ..models import list_no_class_exceptions
        match = next((item for item in list_no_class_exceptions(database_path, arguments["date"]) if item["course"] == arguments["course"]), None)
        return delete_no_class_exception(database_path, match["id"]) if match else None
    if tool_name == "create_note":
        return add_note(database_path, arguments)
    if tool_name == "edit_note":
        if not get_note(database_path, arguments["note_id"]):
            raise ValueError("Note not found")
        return update_note(database_path, arguments["note_id"], arguments["fields"])
    if tool_name == "delete_note":
        if not get_note(database_path, arguments["note_id"]):
            raise ValueError("Note not found")
        delete_note(database_path, arguments["note_id"])
        return {"id": arguments["note_id"], "deleted": True}
    if tool_name == "add_wallet":
        return add_wallet(database_path, arguments)
    if tool_name == "add_payer":
        return add_contributor(database_path, arguments["name"])
    if tool_name == "record_transaction":
        if "course" in arguments and "wallet_id" not in arguments:
            wallet = next((item for item in list_wallets(database_path, True) if item.get("course") == arguments["course"]), None)
            if not wallet:
                raise ValueError("Course wallet not found")
            arguments["wallet_id"] = wallet["id"]
        wallet = get_wallet(database_path, arguments.get("wallet_id"))
        if not wallet or not wallet.get("active"):
            raise ValueError("Active wallet not found")
        return add_budget_entry(database_path, arguments)
    if tool_name == "update_withdrawal_status":
        return update_budget_entry(database_path, arguments["transaction_id"], {"status": arguments["status"]})
    if tool_name == "post_announcement":
        announcement = {key: value for key, value in arguments.items() if key != "options"}
        return add_announcement(database_path, announcement, arguments.get("options", []))
    if tool_name == "cast_poll_vote":
        valid_ids_path = Path(__file__).resolve().parents[2] / "valid_school_ids.txt"
        try:
            valid_ids = {line.strip() for line in valid_ids_path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")}
        except FileNotFoundError:
            valid_ids = set()
        if arguments["school_id"] not in valid_ids:
            raise ValueError("Enter a valid School ID")
        return add_poll_vote(database_path, arguments["announcement_id"], arguments["option_id"], arguments["school_id"])
    raise ValueError("Unknown tool")
