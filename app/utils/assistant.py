import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .rich_text import rich_text_plain
from .schedule import today_manila

NO_NOTE_CONTEXT = "I couldn't find information about that in your Notes."


def classify_message(message):
	text = " ".join(str(message or "").split())
	lower = text.casefold()
	if not text:
		return {"intent": "clarification", "message": "Tell me what you need help with."}
	action = parse_mastercontrol_command(text)
	if action:
		return action
	if any(phrase in lower for phrase in ("my notes", "from my notes", "in my notes", "note about", "notes about")):
		return {"intent": "note_query", "query": _note_query(text)}
	if any(word in lower for word in ("schedule", "class", "classes")):
		return {"intent": "schedule", "date": _relative_date(lower)}
	if any(word in lower for word in ("deadline", "deadlines", "due", "to do", "todo")):
		return {"intent": "deadlines", "start": _relative_date(lower), "course": _course_in(text)}
	if any(word in lower for word in ("search", "find", "look up")):
		return {"intent": "search", "query": re.sub(r"^(search|find|look up)\s*", "", text, flags=re.I).strip()}
	return {"intent": "open_qa", "message": "I can answer questions about your schedule, deadlines, and Notes. For study questions, mention your Notes so I can ground the answer in them."}


def answer_message(database_path, message):
	route = classify_message(message)
	if route["intent"] == "mastercontrol_action":
		return {**route, "message": "I parsed this as a Mastercontrol action. PIN authorization and confirmation are required before anything changes."}
	if route["intent"] == "note_query":
		from ..models import search_note_context

		matches = search_note_context(database_path, route["query"], course=route.get("course", ""))
		if not matches:
			return {**route, "message": NO_NOTE_CONTEXT, "sources": []}
		return {
			**route,
			"message": "Based on your Notes:\n" + "\n".join(f"- {item['title']} ({item['course']}): {item['snippet']}" for item in matches),
			"sources": matches,
		}
	if route["intent"] == "deadlines":
		from ..models import list_tasks

		target = route["start"]
		tasks = [task for task in list_tasks(database_path) if _task_manila_date(task) == target and (not route.get("course") or task["course"] == route["course"])]
		return {**route, "message": _deadline_message(tasks, target), "tasks": tasks, "timezone": "Asia/Manila"}
	if route["intent"] == "schedule":
		from ..models import list_no_class_exceptions
		from .schedule import get_schedule_for_date, serialize_entry

		exceptions = list_no_class_exceptions(database_path, route["date"].isoformat())
		classes = [serialize_entry(entry) for entry in get_schedule_for_date(route["date"], exceptions)]
		return {**route, "date": route["date"].isoformat(), "classes": classes, "exceptions": exceptions, "message": _schedule_message(classes), "timezone": "Asia/Manila"}
	if route["intent"] == "search":
		from ..models import search_content

		results = search_content(database_path, route["query"])
		return {**route, "message": _search_message(results), "results": results}
	return route


def parse_mastercontrol_command(text):
	deadline = re.match(r"(?:set|add|create)\s+deadline\s+(.+?)\s+for\s+([\w ]+?)\s+titled\s+(.+?)(?:\s+for\s+(.+))?$", text, re.I)
	if deadline:
		when, course, title, description = deadline.groups()
		return {"intent": "mastercontrol_action", "tool": "create_deadline", "arguments": {"datetime": when.strip(), "course": course.strip(), "title": title.strip(), "description": (description or title).strip(), "difficulty": "Medium"}}
	no_class = re.match(r"(?:no|cancel)\s+classes?\s+(.+?)\s+(?:on|for)\s+(.+)$", text, re.I)
	if no_class:
		course, target_date = no_class.groups()
		return {"intent": "mastercontrol_action", "tool": "add_no_class_exception", "arguments": {"course": course.strip(), "date": target_date.strip()}}
	restore = re.match(r"restore\s+class(?:es)?\s+(.+?)\s+(?:on|for)\s+(.+)$", text, re.I)
	if restore:
		course, target_date = restore.groups()
		return {"intent": "mastercontrol_action", "tool": "restore_class_exception", "arguments": {"course": course.strip(), "date": target_date.strip()}}
	delete_deadline = re.match(r"(?:delete|remove)\s+deadline\s+(\d+)$", text, re.I)
	if delete_deadline:
		return {"intent": "mastercontrol_action", "tool": "delete_deadline", "arguments": {"deadline_id": delete_deadline.group(1)}}
	edit_deadline = re.match(r"edit\s+deadline\s+(\d+)\s+(.+)$", text, re.I)
	if edit_deadline:
		deadline_id, fields_text = edit_deadline.groups()
		arguments = {"deadline_id": deadline_id}
		title = re.search(r"\btitle\s+(.+?)(?=\s+(?:for|to|at)\b|$)", fields_text, re.I)
		course = re.search(r"\bfor\s+([\w ]+?)(?=\s+(?:title|to|at)\b|$)", fields_text, re.I)
		when = re.search(r"\b(?:to|at)\s+(.+)$", fields_text, re.I)
		if title:
			arguments["title"] = title.group(1).strip()
		if course:
			arguments["course"] = course.group(1).strip()
		if when:
			arguments["datetime"] = when.group(1).strip()
		return {"intent": "mastercontrol_action", "tool": "edit_deadline", "arguments": arguments}
	delete_note = re.match(r"(?:delete|remove)\s+note\s+(\d+)$", text, re.I)
	if delete_note:
		return {"intent": "mastercontrol_action", "tool": "delete_note", "arguments": {"note_id": delete_note.group(1)}}
	edit_note = re.match(r"edit\s+note\s+(\d+)\s+(.+)$", text, re.I)
	if edit_note:
		note_id, fields_text = edit_note.groups()
		arguments = {"note_id": note_id}
		title = re.search(r"\btitle\s+(.+?)(?=\s+(?:course|captioned)\b|$)", fields_text, re.I)
		course = re.search(r"\bcourse\s+(.+?)(?=\s+(?:title|captioned)\b|$)", fields_text, re.I)
		caption = re.search(r"\bcaptioned\s+(.+)$", fields_text, re.I)
		if title:
			arguments["title"] = title.group(1).strip()
		if course:
			arguments["course"] = course.group(1).strip()
		if caption:
			arguments["caption"] = caption.group(1).strip()
		return {"intent": "mastercontrol_action", "tool": "edit_note", "arguments": arguments}
	status = re.match(r"(?:mark|update)\s+withdrawal\s+(\d+)\s+(?:as|to)\s+(pending|spent|cancelled)$", text, re.I)
	if status:
		transaction_id, withdrawal_status = status.groups()
		return {"intent": "mastercontrol_action", "tool": "update_withdrawal_status", "arguments": {"transaction_id": transaction_id, "status": withdrawal_status.casefold()}}
	note = re.match(r"(?:create|add)\s+note\s+(.+?)\s+for\s+([\w ]+?)\s+(?:saying|with|captioned)\s+(.+)$", text, re.I)
	if note:
		title, course, caption = note.groups()
		return {"intent": "mastercontrol_action", "tool": "create_note", "arguments": {"title": title.strip(), "course": course.strip(), "caption": caption.strip()}}
	wallet = re.match(r"(?:create|add)\s+(?:a\s+)?wallet\s+(.+?)(?:\s+for\s+([\w ]+))?$", text, re.I)
	if wallet:
		name, course = wallet.groups()
		arguments = {"wallet_name": name.strip()}
		if course:
			arguments["course"] = course.strip()
		return {"intent": "mastercontrol_action", "tool": "add_wallet", "arguments": arguments}
	payer = re.match(r"(?:add|register)\s+(?:a\s+)?payer\s+(.+)$", text, re.I)
	if payer:
		return {"intent": "mastercontrol_action", "tool": "add_payer", "arguments": {"payer_name": payer.group(1).strip()}}
	transaction = re.match(r"(deposit|withdraw)\s+([0-9]+(?:\.[0-9]{1,2})?)\s+(?:to|from)\s+(.+?)\s+for\s+(.+)$", text, re.I)
	if transaction:
		entry_type, amount, course, reason = transaction.groups()
		return {"intent": "mastercontrol_action", "tool": "record_transaction", "arguments": {"type": entry_type.casefold(), "amount": amount, "course": course.strip(), "reason": reason.strip()}}
	announcement = re.match(r"(?:post|create)\s+announcement\s+(.+?)\s+(?:saying|with message)\s+(.+)$", text, re.I)
	if announcement:
		title, message = announcement.groups()
		return {"intent": "mastercontrol_action", "tool": "post_announcement", "arguments": {"title": title.strip(), "message": message.strip()}}
	return None


def _note_query(text):
	query = re.sub(r"\b(from|in)\s+my\s+notes?\b", "", text, flags=re.I)
	query = re.sub(r"\b(notes?|note)\s+(about|on)\b", "", query, flags=re.I)
	return query.strip(" ?.!\t") or text


def _course_in(text):
	from config import ALLOWED_COURSES

	return next((course for course in ALLOWED_COURSES if course.casefold() in text.casefold()), "")


def _relative_date(text):
	today = today_manila()
	if "tomorrow" in text:
		return today + timedelta(days=1)
	if "yesterday" in text:
		return today - timedelta(days=1)
	return today


def _deadline_message(tasks, target):
	if not tasks:
		return f"Nothing is due on {target.isoformat()}."
	return "Due " + target.isoformat() + ": " + "; ".join(task["title"] for task in tasks)


def _task_manila_date(task):
	try:
		value = datetime.fromisoformat(str(task.get("deadline", "")).replace("Z", "+00:00"))
		if value.tzinfo is None:
			value = value.replace(tzinfo=timezone.utc)
		return value.astimezone(ZoneInfo("Asia/Manila")).date()
	except (TypeError, ValueError):
		return None


def _search_message(results):
	if not results:
		return "I couldn't find matching items."
	return "Matches: " + "; ".join(f"{item['kind']}: {item['title']}" for item in results)


def _schedule_message(classes):
	if not classes:
		return "No classes scheduled."
	return "Classes: " + "; ".join(f"{entry['start']}-{entry['end']} {entry['course']}" for entry in classes)