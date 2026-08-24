import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from .models import (
	add_announcement,
	add_budget_entry,
	add_note,
	add_note_attachments,
	add_poll_vote,
	add_task,
	delete_note,
	delete_task,
	get_budget_entry,
	get_note,
	get_task,
	list_announcements,
	list_budget_entries,
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


def _note_values(data):
	values = {key: str(data.get(key, "")).strip() for key in ("title", "course")}
	values["caption"] = sanitize_rich_text(data.get("caption", ""))
	if not all(values.values()) or not rich_text_plain(values["caption"]):
		return None, "Title, course, and caption are required"
	if len(rich_text_plain(values["caption"])) > 2000:
		return None, "Caption must be 2000 characters or fewer"
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
		datetime.fromisoformat(data["deadline"].replace("Z", "+00:00"))
	except ValueError:
		return "Deadline must be a valid ISO datetime"
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
	entries = list_budget_entries(current_app.config["DATABASE_PATH"])
	balance = sum(entry["amount"] if entry["type"] == "deposit" else -entry["amount"] for entry in entries)
	return jsonify(entries=entries, balance=round(balance, 2))


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
	if len(rich_text_plain(body)) > 2000:
		return jsonify(error="Message must be 2000 characters or fewer"), 400
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
	if query in {"class fund used today", "class fund used this week", "class fund use this month"}:
		entries = list_budget_entries(current_app.config["DATABASE_PATH"])
		today = datetime.now().date()
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
		deadline = task["deadline"][:10]
		if start <= deadline <= end and (not parsed.get("course") or task["course"].lower() == parsed["course"].lower()):
			tasks.append(task)
	return jsonify(label=parsed["label"], tasks=tasks)


@main.post("/api/tasks")
def create_task():
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	error = _validate(data)
	if error:
		return jsonify(error=error), 400
	attachment = request.files.get("attachment")
	values = {key: str(data.get(key, "")).strip() for key in ("title", "course", "description", "deadline")}
	values["difficulty"] = data.get("difficulty", "Medium")
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
	reason = str(data.get("reason", "")).strip()
	try:
		amount = float(data.get("amount", ""))
	except (TypeError, ValueError):
		return jsonify(error="Amount must be a valid number"), 400
	if entry_type not in {"deposit", "withdraw"}:
		return jsonify(error="Choose deposit or withdraw"), 400
	if amount <= 0:
		return jsonify(error="Amount must be greater than zero"), 400
	if not reason:
		return jsonify(error="Reason is required"), 400
	return jsonify(entry=add_budget_entry(current_app.config["DATABASE_PATH"], {"type": entry_type, "amount": round(amount, 2), "reason": reason})), 201


@main.patch("/api/budget/<int:entry_id>")
def update_budget(entry_id):
	data = _payload()
	if data.get("pin") != current_app.config["TASK_PIN"]:
		return jsonify(error="Invalid PIN"), 403
	entry = get_budget_entry(current_app.config["DATABASE_PATH"], entry_id)
	if not entry:
		return jsonify(error="Budget entry not found"), 404
	if entry["type"] != "withdraw" or entry["status"] != "pending":
		return jsonify(error="Only pending withdrawals can be resolved"), 400
	action = str(data.get("action", "")).strip().lower()
	if action == "cancel":
		values = {"type": "deposit", "status": "cancelled"}
	elif action == "spent":
		values = {"status": "spent"}
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
	if not get_task(current_app.config["DATABASE_PATH"], task_id):
		return jsonify(error="Task not found"), 404
	error = _validate({**(get_task(current_app.config["DATABASE_PATH"], task_id) or {}), **data})
	if error:
		return jsonify(error=error), 400
	return jsonify(task=update_task(current_app.config["DATABASE_PATH"], task_id, data))


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
