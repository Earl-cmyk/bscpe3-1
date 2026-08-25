import re
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from .models import (
	add_announcement,
	add_budget_entry,
	add_contributor,
	add_no_class_exception,
	add_note,
	add_note_attachments,
	add_poll_vote,
	add_task,
	add_wallet,
	delete_no_class_exception,
	delete_note,
	delete_task,
	get_budget_entry,
	get_note,
	get_task,
	get_wallet,
	list_budget_audit_events,
	list_contributors,
	list_wallets,
	list_announcements,
	list_budget_entries,
	list_no_class_exceptions,
	list_notes,
	list_tasks,
	list_upcoming_tasks,
	search_content,
	update_budget_entry,
	update_note,
	update_task,
)
from .utils.query_parser import parse_query
from .utils.rich_text import rich_text_plain, sanitize_rich_text
from .utils.schedule import DAY_NAMES, COURSE_SHORT, get_schedule_for_date, parse_manila_date, parse_manila_datetime, serialize_entry, today_manila
from config import ALLOWED_COURSES, ALLOWED_DIFFICULTIES



main = Blueprint("main", __name__)


@main.get("/")
def index():
	return render_template("index.html")


@main.get("/tasks")
def tasks_page():
	return render_template("tasks.html")


@main.get("/budget")
def budget_page():
	return render_template("budget.html")


@main.get("/announcements")
def announcements_page():
	return render_template("announcements.html")


@main.get("/notes")
def notes_page():
	return render_template("notes.html")


def _payload():
	return request.get_json(silent=True) or request.form


@main.post("/api/verify-pin")
def verify_pin():
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	return jsonify(ok=True)


def _pin_valid(data):
	return str(data.get("pin", "")) == current_app.config["TASK_PIN"]


def _course_code(value):
	value = str(value or "").strip()
	if value in ALLOWED_COURSES:
		return value
	for title, short in COURSE_SHORT.items():
		if value.casefold() in {title.casefold(), short.casefold()}:
			return short
	return None


@main.get("/api/schedule")
def get_schedule():
	try:
		target_date = parse_manila_date(request.args.get("date", today_manila().isoformat()))
	except ValueError:
		return jsonify(error="Date must be YYYY-MM-DD"), 400
	exceptions = list_no_class_exceptions(current_app.config["DATABASE_PATH"], target_date.isoformat())
	entries = get_schedule_for_date(target_date, exceptions)
	return jsonify(date=target_date.isoformat(), day_name=DAY_NAMES[target_date.weekday()], classes=[serialize_entry(entry) for entry in entries], exceptions=exceptions, timezone="Asia/Manila")


@main.post("/api/schedule/exceptions")
def create_schedule_exception():
	data = _payload()
	if not _pin_valid(data):
		return jsonify(error="Invalid PIN"), 403
	try:
		target_date = parse_manila_date(data.get("date", ""))
	except ValueError:
		return jsonify(error="Date must be YYYY-MM-DD"), 400
	course = _course_code(data.get("course"))
	if not course:
		return jsonify(error="Invalid course"), 400
	return jsonify(exception=add_no_class_exception(current_app.config["DATABASE_PATH"], target_date.isoformat(), course)), 201


@main.delete("/api/schedule/exceptions/<int:exception_id>")
def remove_schedule_exception(exception_id):
	data = _payload()
	if not _pin_valid(data):
		return jsonify(error="Invalid PIN"), 403
	exception = delete_no_class_exception(current_app.config["DATABASE_PATH"], exception_id)
	return (jsonify(exception=exception), 200) if exception else (jsonify(error="Exception not found"), 404)


def _note_values(data):
	values = {key: str(data.get(key, "")).strip() for key in ("title", "course")}
	values["caption"] = sanitize_rich_text(data.get("caption", ""))
	if not all(values.values()) or not rich_text_plain(values["caption"]):
		return None, "Title, course, and caption are required"
	if values["course"] not in ALLOWED_COURSES:
		return None, "Invalid course"
	return values, None


def _save_attachments(files):
	attachments = []
	storage = _storage_client()
	for attachment in files:
		if not attachment or not attachment.filename:
			continue
		filename = secure_filename(attachment.filename)
		if not filename:
			return None, "Invalid attachment filename"
		stored = f"{uuid4().hex}_{filename}"
		_save_attachment(attachment, stored, storage)
		attachments.append({"name": filename, "path": stored, "type": attachment.mimetype or "application/octet-stream"})
	return attachments, None


def _storage_client():
	if not current_app.config.get("SUPABASE_URL") or not current_app.config.get("SUPABASE_SECRET_KEY"):
		return None
	from supabase import create_client
	return create_client(current_app.config["SUPABASE_URL"], current_app.config["SUPABASE_SECRET_KEY"])


def _save_attachment(attachment, stored, storage=None):
	if storage:
		storage.storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).upload(
			stored,
			attachment.stream.read(),
			{"content-type": attachment.mimetype or "application/octet-stream", "upsert": "false"},
		)
	else:
		attachment.save(Path(current_app.config["UPLOAD_FOLDER"]) / stored)


def _attachment_url(path):
	if not path:
		return None
	storage = _storage_client()
	if not storage:
		return url_for("main.uploaded_file", filename=path)
	try:
		result = storage.storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).create_signed_url(path, 3600)
	except Exception:
		return None
	return result.get("signedURL") or result.get("signedUrl")


@main.get("/api/notes")
def get_notes():
	course = request.args.get("course", "").strip()
	if course and course not in ALLOWED_COURSES:
		return jsonify(error="Invalid course"), 400
	return jsonify(notes=list_notes(current_app.config["DATABASE_PATH"], course))


@main.post("/api/notes")
def create_note():
	data = request.form
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	values, error = _note_values(data)
	if error:
		return jsonify(error=error), 400
	attachments, error = _save_attachments(request.files.getlist("attachments"))
	if error:
		return jsonify(error=error), 400
	values["attachments"] = attachments
	return jsonify(note=add_note(current_app.config["DATABASE_PATH"], values)), 201


@main.get("/api/notes/<int:note_id>")
def note_detail(note_id):
	note = get_note(current_app.config["DATABASE_PATH"], note_id)
	return (jsonify(note=note), 200) if note else (jsonify(error="Note not found"), 404)


@main.patch("/api/notes/<int:note_id>")
def edit_note(note_id):
	if request.form.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	if not get_note(current_app.config["DATABASE_PATH"], note_id):
		return jsonify(error="Note not found"), 404
	values, error = _note_values(request.form)
	if error:
		return jsonify(error=error), 400
	attachments, error = _save_attachments(request.files.getlist("attachments"))
	if error:
		return jsonify(error=error), 400
	updated = update_note(current_app.config["DATABASE_PATH"], note_id, values)
	return jsonify(note=add_note_attachments(current_app.config["DATABASE_PATH"], updated["id"], attachments))


@main.delete("/api/notes/<int:note_id>")
def remove_note(note_id):
	data = request.get_json(silent=True) or request.form
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	if not get_note(current_app.config["DATABASE_PATH"], note_id):
		return jsonify(error="Note not found"), 404
	delete_note(current_app.config["DATABASE_PATH"], note_id)
	return jsonify(ok=True)


def _validate(data):
	missing = [field for field in ("title", "course", "description", "deadline") if not str(data.get(field, "")).strip()]
	if missing:
		return f"Missing required field: {missing[0]}"
	if data["course"] not in ALLOWED_COURSES and data["course"] != "Other":
		return "Invalid course"
	if data.get("difficulty", "Medium") not in ALLOWED_DIFFICULTIES:
		return "Invalid difficulty"
	try:
		parse_manila_datetime(data["deadline"])
	except ValueError:
		return "Deadline must be a valid date and time"
	return None


@main.get("/api/tasks")
def get_tasks():
	return jsonify(tasks=list_tasks(current_app.config["DATABASE_PATH"], request.args.get("search", "").strip()))


@main.get("/api/search")
def search():
	term = request.args.get("q", "").strip()
	if not term:
		return jsonify(results=[])
	kind = request.args.get("kind", "").strip()
	if kind not in ("", "Task", "Note", "Announcement"):
		return jsonify(error="Invalid result type"), 400
	return jsonify(results=search_content(current_app.config["DATABASE_PATH"], term, kind=kind, course=request.args.get("course", "").strip()))


@main.get("/api/budget")
def get_budget():
	wallet_id = request.args.get("wallet_id", type=int)
	entries = list_budget_entries(current_app.config["DATABASE_PATH"], wallet_id)
	active_entries = [entry for entry in entries if entry["status"] != "cancelled"]
	balance = sum(Decimal(str(entry["amount"])) if entry["type"] == "deposit" else -Decimal(str(entry["amount"])) for entry in active_entries)
	deposits = sum(Decimal(str(entry["amount"])) for entry in active_entries if entry["type"] == "deposit")
	withdrawals = sum(Decimal(str(entry["amount"])) for entry in active_entries if entry["type"] == "withdraw")
	return jsonify(entries=entries, balance=float(balance), wallets=list_wallets(current_app.config["DATABASE_PATH"], True), contributors=list_contributors(current_app.config["DATABASE_PATH"], True), deposits=float(deposits), withdrawals=float(withdrawals), audit=list_budget_audit_events(current_app.config["DATABASE_PATH"]))


@main.get("/api/wallets")
def get_wallets():
	return jsonify(wallets=list_wallets(current_app.config["DATABASE_PATH"], True))


@main.post("/api/wallets")
def create_wallet():
	data = _payload()
	if not _pin_valid(data):
		return jsonify(error="Invalid PIN"), 403
	name = str(data.get("name", "")).strip()
	course = _course_code(data.get("course")) if data.get("course") else None
	if not name:
		return jsonify(error="Wallet name is required"), 400
	if data.get("course") and not course:
		return jsonify(error="Invalid course"), 400
	try:
		return jsonify(wallet=add_wallet(current_app.config["DATABASE_PATH"], {"name": name, "course": course})), 201
	except sqlite3.IntegrityError:
		return jsonify(error="Wallet name already exists"), 409


@main.get("/api/contributors")
def get_contributors():
	return jsonify(contributors=list_contributors(current_app.config["DATABASE_PATH"], True))


@main.post("/api/contributors")
def create_contributor():
	data = _payload()
	if not _pin_valid(data):
		return jsonify(error="Invalid PIN"), 403
	name = str(data.get("name", "")).strip()
	if not name or len(name) > 120:
		return jsonify(error="Contributor name is required"), 400
	try:
		return jsonify(contributor=add_contributor(current_app.config["DATABASE_PATH"], name)), 201
	except sqlite3.IntegrityError:
		return jsonify(error="Contributor already exists"), 409


@main.get("/api/budget/audit")
def get_budget_audit():
	return jsonify(events=list_budget_audit_events(current_app.config["DATABASE_PATH"], request.args.get("entry_id", type=int)))


@main.get("/api/dashboard")
def get_dashboard():
	entries = list_budget_entries(current_app.config["DATABASE_PATH"])
	balance = sum(
		entry["amount"] if entry["type"] == "deposit" and entry["status"] != "cancelled" else -entry["amount"]
		if entry["type"] == "withdraw" and entry["status"] != "cancelled"
		else 0
		for entry in entries
	)
	return jsonify(
		announcements=list_announcements(current_app.config["DATABASE_PATH"], limit=5),
		balance=round(balance, 2),
		deadlines=list_upcoming_tasks(current_app.config["DATABASE_PATH"], limit=3),
	)


@main.get("/api/announcements")
def get_announcements():
	return jsonify(announcements=list_announcements(current_app.config["DATABASE_PATH"]))


@main.post("/api/announcements")
def create_announcement():
	data = request.form
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	title = data.get("title", "").strip()
	body = sanitize_rich_text(data.get("body", ""))
	if not title or not rich_text_plain(body):
		return jsonify(error="Title and message are required"), 400
	link_url = data.get("link_url", "").strip() or None
	if link_url:
		parts = urlsplit(link_url)
		if parts.scheme not in {"http", "https"} or not parts.netloc:
			return jsonify(error="Link must be a valid HTTP or HTTPS URL"), 400
	options = []
	for option in request.form.getlist("options"):
		label = option.strip()
		if label and label not in options:
			options.append(label)
	if options and len(options) < 2:
		return jsonify(error="A poll needs at least two options"), 400
	attachment = request.files.get("attachment")
	values = {"title": title, "body": body, "link_url": link_url}
	if attachment and attachment.filename:
		filename = secure_filename(attachment.filename)
		if not filename:
			return jsonify(error="Invalid attachment filename"), 400
		stored = f"{uuid4().hex}_{filename}"
		_save_attachment(attachment, stored, _storage_client())
		values.update(attachment_name=filename, attachment_path=stored, attachment_type=attachment.mimetype or "application/octet-stream")
	return jsonify(announcement=add_announcement(current_app.config["DATABASE_PATH"], values, options)), 201


@main.post("/api/announcements/<int:announcement_id>/vote")
def vote_announcement(announcement_id):
	school_id = request.get_json(silent=True).get("school_id", "").strip() if request.is_json else request.form.get("school_id", "").strip()
	try:
		valid_ids = {
			line.strip()
			for line in Path(current_app.config["BASE_DIR"]) .joinpath("valid_school_ids.txt").read_text().splitlines()
			if line.strip() and not line.lstrip().startswith("#")
		}
	except FileNotFoundError:
		valid_ids = set()
	if not school_id or school_id not in valid_ids:
		return jsonify(error="Enter a valid School ID"), 400
	data = request.get_json(silent=True) or request.form
	try:
		announcement = add_poll_vote(current_app.config["DATABASE_PATH"], announcement_id, int(data.get("option_id", 0)), school_id)
	except sqlite3.IntegrityError:
		return jsonify(error="This School ID has already voted"), 409
	except Exception as error:
		from psycopg.errors import UniqueViolation
		if isinstance(error, UniqueViolation):
			return jsonify(error="This School ID has already voted"), 409
		raise
	if announcement is None:
		return jsonify(error="Announcement or poll option not found"), 404
	return jsonify(announcement=announcement)


@main.get("/api/query")
def query_tasks():
	query = request.args.get("q", "").strip().lower()
	if query in {"what is my schedule for today?", "what is my schedule for today", "schedule today", "my schedule today"}:
		target_date = today_manila()
		exceptions = list_no_class_exceptions(current_app.config["DATABASE_PATH"], target_date.isoformat())
		return jsonify(label="Schedule for today", date=target_date.isoformat(), classes=[serialize_entry(entry) for entry in get_schedule_for_date(target_date, exceptions)], exceptions=exceptions, timezone="Asia/Manila")
	if query in {"class fund used today", "class fund used this week", "class fund use this month"}:
		entries = list_budget_entries(current_app.config["DATABASE_PATH"])
		today = today_manila()
		if query.endswith("today"):
			start = end = today
			label = "Class fund used today"
		elif query.endswith("week"):
			start = today.fromordinal(today.toordinal() - today.weekday())
			end = start.fromordinal(start.toordinal() + 6)
			label = "Class fund used this week"
		else:
			start = today.replace(day=1)
			end = today
			label = "Class fund used this month"
		used = [entry for entry in entries if entry["type"] == "withdraw" and entry["status"] == "spent" and start.isoformat() <= entry["created_at"][:10] <= end.isoformat()]
		return jsonify(label=label, entries=used, total=round(sum(entry["amount"] for entry in used), 2))
	parsed = parse_query(request.args.get("q", ""))
	if not parsed:
		return jsonify(error="Try deadlines today, deadlines this week, deadlines this month, or to do for HDL today"), 400
	start, end = parsed["start"].isoformat(), parsed["end"].isoformat()
	tasks = []
	for task in list_tasks(current_app.config["DATABASE_PATH"]):
		try:
			deadline = datetime.fromisoformat(task["deadline"].replace("Z", "+00:00"))
			if deadline.tzinfo is None:
				deadline = deadline.replace(tzinfo=timezone.utc)
			deadline = deadline.astimezone(ZoneInfo("Asia/Manila")).date().isoformat()
		except (TypeError, ValueError):
			deadline = task["deadline"][:10]
		if start <= deadline <= end and (not parsed.get("course") or task["course"].lower() == parsed["course"].lower()):
			tasks.append(task)
	return jsonify(label=parsed["label"], tasks=tasks)


@main.post("/api/assistant")
def assistant_command():
	data = _payload()
	command = str(data.get("command", "")).strip()
	if not command:
		return jsonify(assistant="R3-1N", error="Enter a command"), 400
	if not _pin_valid(data):
		return jsonify(assistant="R3-1N", error="PIN required", requires_pin=True), 403
	database_path = current_app.config["DATABASE_PATH"]
	deadline_match = re.match(r"^set deadline (.+?) for (.+?) titled (.+?) for (.+)$", command, re.I)
	if deadline_match:
		deadline_text, course_text, title, reason = [part.strip() for part in deadline_match.groups()]
		course = _course_code(course_text)
		if not course:
			return jsonify(assistant="R3-1N", error="Invalid course"), 400
		try:
			deadline = parse_manila_datetime(deadline_text)
		except ValueError:
			return jsonify(assistant="R3-1N", error="Deadline must be a valid date and time"), 400
		task = add_task(database_path, {"title": title, "course": course, "description": sanitize_rich_text(reason), "deadline": deadline, "difficulty": "Medium"})
		return jsonify(assistant="R3-1N", intent="set_deadline", message=f"Deadline set for {course}.", task=task), 201
	no_class_match = re.match(r"^no classes (.+?) (?:on|for) (.+)$", command, re.I)
	if no_class_match:
		course = _course_code(no_class_match.group(1))
		if not course:
			return jsonify(assistant="R3-1N", error="Invalid course"), 400
		try:
			target_date = parse_manila_date(no_class_match.group(2))
		except ValueError:
			return jsonify(assistant="R3-1N", error="Date must be YYYY-MM-DD"), 400
		exception = add_no_class_exception(database_path, target_date.isoformat(), course)
		return jsonify(assistant="R3-1N", intent="no_classes", message=f"{course} marked as no class on {target_date.isoformat()}.", exception=exception), 201
	budget_match = re.match(r"^(deposit|withdraw)\s+([0-9]+(?:\.[0-9]{1,2})?)\s+to\s+(.+?)\s+for\s+(.+)$", command, re.I)
	if budget_match:
		entry_type, amount_text, wallet_text, reason = budget_match.groups()
		amount = Decimal(amount_text)
		if amount <= 0:
			return jsonify(assistant="R3-1N", error="Amount must be greater than zero"), 400
		wallet = next((item for item in list_wallets(database_path, True) if item["name"].casefold() == wallet_text.strip().casefold() or (item.get("course") and item["course"].casefold() == wallet_text.strip().casefold())), None)
		if not wallet or not wallet.get("course"):
			return jsonify(assistant="R3-1N", error="Choose a valid course wallet"), 400
		entry = add_budget_entry(database_path, {"type": entry_type.lower(), "amount": float(amount.quantize(Decimal("0.01"))), "reason": sanitize_rich_text(reason), "wallet_id": wallet["id"], "course": wallet["course"]})
		return jsonify(assistant="R3-1N", intent=entry_type.lower(), message=f"{entry_type.title()} recorded for {wallet['name']}.", entry=entry), 201
	return jsonify(assistant="R3-1N", error="Use Set deadline ..., No classes ..., Deposit <amount> to <course> for <reason>, or Withdraw <amount> to <course> for <reason>"), 400


@main.post("/api/tasks")
def create_task():
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	error = _validate(data)
	if error:
		return jsonify(error=error), 400
	attachment = request.files.get("attachment")
	values = {key: str(data.get(key, "")).strip() for key in ("title", "course", "deadline")}
	values["description"] = sanitize_rich_text(data.get("description", ""))
	values["difficulty"] = data.get("difficulty", "Medium")
	values["deadline"] = parse_manila_datetime(values["deadline"])
	if attachment and attachment.filename:
		filename = secure_filename(attachment.filename)
		if not filename:
			return jsonify(error="Invalid attachment filename"), 400
		stored = f"{uuid4().hex}_{filename}"
		_save_attachment(attachment, stored, _storage_client())
		values.update(attachment_name=filename, attachment_path=stored, attachment_type=attachment.mimetype or "application/octet-stream")
	return jsonify(task=add_task(current_app.config["DATABASE_PATH"], values)), 201


@main.post("/api/budget")
def create_budget_entry():
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	entry_type = str(data.get("type", "")).strip().lower()
	reason = sanitize_rich_text(data.get("reason", ""))
	try:
		amount = Decimal(str(data.get("amount", "")))
	except (InvalidOperation, ValueError):
		return jsonify(error="Amount must be a valid number"), 400
	if entry_type not in {"deposit", "withdraw"}:
		return jsonify(error="Choose deposit or withdraw"), 400
	if amount <= 0:
		return jsonify(error="Amount must be greater than zero"), 400
	if not rich_text_plain(reason):
		return jsonify(error="Reason is required"), 400
	payer_names = data.get("payer_names", [])
	if isinstance(payer_names, str):
		try:
			payer_names = json.loads(payer_names)
		except (TypeError, ValueError):
			payer_names = re.split(r"[\n,]", payer_names)
	if not isinstance(payer_names, list):
		return jsonify(error="Payer list must be an array"), 400
	payer_names = list(dict.fromkeys(str(name).strip() for name in payer_names if str(name).strip()))
	if len(payer_names) > 100 or any(len(name) > 120 for name in payer_names):
		return jsonify(error="Payer list is too large"), 400
	try:
		wallet_id = int(data.get("wallet_id")) if data.get("wallet_id") else None
	except (TypeError, ValueError):
		wallet_id = None
	if not wallet_id and data.get("course"):
		course = _course_code(data.get("course"))
		wallet = next((item for item in list_wallets(current_app.config["DATABASE_PATH"], True) if item.get("course") == course), None)
		wallet_id = wallet["id"] if wallet else None
	wallet = get_wallet(current_app.config["DATABASE_PATH"], wallet_id) if wallet_id else None
	if not wallet or not wallet.get("active") or not wallet.get("course"):
		return jsonify(error="Choose a course wallet"), 400
	try:
		contributor_id = int(data.get("contributor_id")) if data.get("contributor_id") else None
	except (TypeError, ValueError):
		contributor_id = None
	contributors = list_contributors(current_app.config["DATABASE_PATH"], True)
	if not contributor_id or not any(item["id"] == contributor_id for item in contributors):
		return jsonify(error="Choose a contributor"), 400
	attachments, error = _save_attachments(request.files.getlist("attachments")) if request.files else ([], None)
	if error:
		return jsonify(error=error), 400
	attachment = attachments[0] if attachments else {}
	entry = add_budget_entry(current_app.config["DATABASE_PATH"], {"type": entry_type, "amount": float(amount.quantize(Decimal("0.01"))), "reason": reason, "wallet_id": wallet_id, "course": wallet["course"], "contributor_id": contributor_id, "payer_names": payer_names, **{f"attachment_{key}": attachment.get(key) for key in ("name", "path", "type")}})
	return jsonify(entry=entry), 201


@main.patch("/api/budget/<int:entry_id>")
def update_budget(entry_id):
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	entry = get_budget_entry(current_app.config["DATABASE_PATH"], entry_id)
	if not entry:
		return jsonify(error="Budget entry not found"), 404
	action = str(data.get("action", "")).strip().lower()
	values = {}
	if "payer_names" in data:
		payer_names = data.get("payer_names")
		if isinstance(payer_names, str):
			try:
				payer_names = json.loads(payer_names)
			except (TypeError, ValueError):
				payer_names = re.split(r"[\n,]", payer_names)
		if not isinstance(payer_names, list):
			return jsonify(error="Payer list must be an array"), 400
		values["payer_names"] = list(dict.fromkeys(str(name).strip() for name in payer_names if str(name).strip()))
	if not action and values:
		return jsonify(entry=update_budget_entry(current_app.config["DATABASE_PATH"], entry_id, values))
	if entry["type"] != "withdraw" or entry["status"] != "pending":
		return jsonify(error="Only pending withdrawals can be resolved"), 400
	if action == "cancel":
		values.update({"status": "cancelled"})
	elif action == "spent":
		values["status"] = "spent"
	else:
		return jsonify(error="Choose cancel or spent"), 400
	return jsonify(entry=update_budget_entry(current_app.config["DATABASE_PATH"], entry_id, values))


@main.route("/api/tasks/<int:task_id>", methods=["GET", "PATCH"])
def task_detail(task_id):
	if request.method == "GET":
		task = get_task(current_app.config["DATABASE_PATH"], task_id)
		return (jsonify(task=task), 200) if task else (jsonify(error="Task not found"), 404)
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	existing = get_task(current_app.config["DATABASE_PATH"], task_id)
	if not existing:
		return jsonify(error="Task not found"), 404
	error = _validate({**existing, **data})
	if error:
		return jsonify(error=error), 400
	values = dict(data)
	if "description" in values:
		values["description"] = sanitize_rich_text(values["description"])
	if "deadline" in values:
		values["deadline"] = parse_manila_datetime(values["deadline"])
	return jsonify(task=update_task(current_app.config["DATABASE_PATH"], task_id, values))


@main.delete("/api/tasks/<int:task_id>")
def remove_task(task_id):
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	if not get_task(current_app.config["DATABASE_PATH"], task_id):
		return jsonify(error="Task not found"), 404
	delete_task(current_app.config["DATABASE_PATH"], task_id)
	return jsonify(ok=True)


@main.get("/uploads/<path:filename>")
def uploaded_file(filename):
	storage = _storage_client()
	if storage:
		try:
			result = storage.storage.from_(current_app.config["SUPABASE_STORAGE_BUCKET"]).create_signed_url(filename, 3600)
		except Exception:
			return jsonify(error="Attachment is unavailable"), 404
		url = result.get("signedURL") or result.get("signedUrl")
		if not url:
			return jsonify(error="Attachment is unavailable"), 404
		return redirect(url)
	return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename, as_attachment=request.args.get("download") == "1")


@main.get("/health")
def health():
	return jsonify(status="ok")
