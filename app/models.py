import json
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager


class _PostgresConnection:
	def __init__(self, connection):
		self._connection = connection

	def execute(self, query, params=()):
		return self._connection.execute(query.replace("?", "%s"), params)

	def commit(self):
		self._connection.commit()

	def rollback(self):
		self._connection.rollback()

	def close(self):
		self._connection.close()


@contextmanager
def get_connection(database_path):
	is_postgres = str(database_path).startswith(("postgres://", "postgresql://"))
	if is_postgres:
		from psycopg import connect
		from psycopg.rows import dict_row

		connection = _PostgresConnection(connect(database_path, row_factory=dict_row))
	else:
		connection = sqlite3.connect(database_path)
		connection.row_factory = sqlite3.Row
	if is_postgres:
		connection.execute("SET TIME ZONE 'UTC'")
	try:
		yield connection
		connection.commit()
	except Exception:
		connection.rollback()
		raise
	finally:
		connection.close()


def init_db(database_path):
	if str(database_path).startswith(("postgres://", "postgresql://")):
		return
	with get_connection(database_path) as connection:
		connection.execute("PRAGMA foreign_keys = ON")
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS tasks (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL,
				course TEXT NOT NULL,
				description TEXT NOT NULL,
				deadline TEXT NOT NULL,
				difficulty TEXT NOT NULL DEFAULT 'Medium',
				completed INTEGER NOT NULL DEFAULT 0,
				attachment_name TEXT,
				attachment_path TEXT,
				attachment_type TEXT,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS budget_entries (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				type TEXT NOT NULL CHECK(type IN ('deposit', 'withdraw')),
				amount REAL NOT NULL CHECK(amount > 0),
				reason TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'spent', 'cancelled')),
				created_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS wallets (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL UNIQUE,
				course TEXT,
				active INTEGER NOT NULL DEFAULT 1,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS contributors (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL UNIQUE,
				active INTEGER NOT NULL DEFAULT 1,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS budget_audit_events (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				entry_id INTEGER,
				event_type TEXT NOT NULL,
				actor TEXT NOT NULL DEFAULT 'system',
				payload TEXT NOT NULL DEFAULT '{}',
				created_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS announcements (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL,
				body TEXT NOT NULL,
				link_url TEXT,
				attachment_name TEXT,
				attachment_path TEXT,
				attachment_type TEXT,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS poll_options (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
				label TEXT NOT NULL,
				position INTEGER NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS poll_votes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				announcement_id INTEGER NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
				option_id INTEGER NOT NULL REFERENCES poll_options(id) ON DELETE CASCADE,
				school_id TEXT NOT NULL,
				created_at TEXT NOT NULL,
				UNIQUE(announcement_id, school_id)
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS notes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				title TEXT NOT NULL,
				course TEXT NOT NULL,
				caption TEXT NOT NULL,
				attachment_name TEXT,
				attachment_path TEXT,
				attachment_type TEXT,
				created_at TEXT NOT NULL,
				updated_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS note_attachments (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
				name TEXT NOT NULL,
				path TEXT NOT NULL,
				type TEXT NOT NULL,
				created_at TEXT NOT NULL
			)
			"""
		)
		connection.execute(
			"""
			CREATE TABLE IF NOT EXISTS no_class_exceptions (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				date TEXT NOT NULL,
				course TEXT NOT NULL,
				created_at TEXT NOT NULL,
				UNIQUE(date, course)
			)
			"""
		)
		legacy_notes = connection.execute(
			"SELECT id, attachment_name, attachment_path, attachment_type, created_at FROM notes WHERE attachment_path IS NOT NULL"
		).fetchall()
		for note in legacy_notes:
			connection.execute(
				"INSERT INTO note_attachments (note_id, name, path, type, created_at) SELECT ?, ?, ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM note_attachments WHERE note_id = ? AND path = ?)",
				(note["id"], note["attachment_name"] or note["attachment_path"], note["attachment_path"], note["attachment_type"] or "application/octet-stream", note["created_at"], note["id"], note["attachment_path"]),
			)
		announcement_columns = {row["name"] for row in connection.execute("PRAGMA table_info(announcements)").fetchall()}
		if "title" not in announcement_columns:
			connection.execute("ALTER TABLE announcements ADD COLUMN title TEXT NOT NULL DEFAULT 'Announcement'")
		if "link_url" not in announcement_columns:
			connection.execute("ALTER TABLE announcements ADD COLUMN link_url TEXT")
		if "attachment_type" not in announcement_columns:
			connection.execute("ALTER TABLE announcements ADD COLUMN attachment_type TEXT")
		if "updated_at" not in announcement_columns:
			connection.execute("ALTER TABLE announcements ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
		if "link" in announcement_columns:
			connection.execute("UPDATE announcements SET link_url = link WHERE link_url IS NULL")
		connection.execute("UPDATE announcements SET updated_at = created_at WHERE updated_at = ''")
		option_columns = {row["name"] for row in connection.execute("PRAGMA table_info(poll_options)").fetchall()}
		if "position" not in option_columns:
			connection.execute("ALTER TABLE poll_options ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
		connection.execute(
			"CREATE UNIQUE INDEX IF NOT EXISTS idx_poll_votes_announcement_school ON poll_votes (announcement_id, school_id)"
		)
		budget_columns = {row["name"] for row in connection.execute("PRAGMA table_info(budget_entries)").fetchall()}
		if "status" not in budget_columns:
			connection.execute("ALTER TABLE budget_entries ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
		for column, definition in {
			"wallet_id": "INTEGER",
			"course": "TEXT",
			"contributor_id": "INTEGER",
			"attachment_name": "TEXT",
			"attachment_path": "TEXT",
			"attachment_type": "TEXT",
		}.items():
			if column not in budget_columns:
				connection.execute(f"ALTER TABLE budget_entries ADD COLUMN {column} {definition}")
		from config import ALLOWED_COURSES
		now = datetime.now(timezone.utc).isoformat()
		connection.execute(
			"INSERT OR IGNORE INTO wallets (name, course, created_at, updated_at) VALUES (?, NULL, ?, ?)",
			("Unassigned", now, now),
		)
		for course in ALLOWED_COURSES:
			connection.execute(
				"INSERT OR IGNORE INTO wallets (name, course, created_at, updated_at) VALUES (?, ?, ?, ?)",
			(course, course, now, now),
			)
		unassigned = connection.execute("SELECT id FROM wallets WHERE name = 'Unassigned'").fetchone()[0]
		connection.execute("UPDATE budget_entries SET wallet_id = ? WHERE wallet_id IS NULL", (unassigned,))
		connection.execute("CREATE INDEX IF NOT EXISTS idx_budget_entries_wallet_created ON budget_entries (wallet_id, created_at DESC, id DESC)")
		connection.execute("CREATE INDEX IF NOT EXISTS idx_budget_audit_events_entry ON budget_audit_events (entry_id, created_at DESC, id DESC)")
		legacy = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='deadlines'").fetchone()
		if legacy and connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0:
			rows = connection.execute("SELECT title, due_date, notes, completed FROM deadlines").fetchall()
			now = datetime.now(timezone.utc).isoformat()
			for row in rows:
				deadline = _normalize_datetime(row["due_date"])
				connection.execute(
					"INSERT INTO tasks (title, course, description, deadline, completed, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
					(row["title"], "Other", row["notes"] or "No description provided.", deadline, row["completed"], now, now),
				)


def _normalize_datetime(value):
	try:
		parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
		if parsed.tzinfo is None:
			parsed = parsed.replace(tzinfo=timezone.utc)
		return parsed.astimezone(timezone.utc).isoformat()
	except (TypeError, ValueError):
		return value


def _row_to_dict(row):
	return dict(row) if row else None


def _inserted_id(row):
	return row["id"] if isinstance(row, dict) else row[0]


def list_tasks(database_path, search=""):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM tasks"
		params = []
		if search:
			query += " WHERE title LIKE ? OR description LIKE ? OR course LIKE ?"
			term = f"%{search}%"
			params = [term, term, term]
		query += " ORDER BY completed, deadline, id"
		return [_row_to_dict(row) for row in connection.execute(query, params).fetchall()]


def list_upcoming_tasks(database_path, limit=3):
	with get_connection(database_path) as connection:
		completed_value = "FALSE" if str(database_path).startswith(("postgres://", "postgresql://")) else "0"
		rows = connection.execute(
			f"""
			SELECT * FROM tasks
			WHERE completed = {completed_value} AND deadline >= ?
			ORDER BY deadline, id
			LIMIT ?
			""",
			(datetime.now(timezone.utc).isoformat(), limit),
		).fetchall()
		return [_row_to_dict(row) for row in rows]


def get_task(database_path, task_id):
	with get_connection(database_path) as connection:
		return _row_to_dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def add_task(database_path, task):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"INSERT INTO tasks (title, course, description, deadline, difficulty, attachment_name, attachment_path, attachment_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
			(task["title"], task["course"], task["description"], task["deadline"], task["difficulty"], task.get("attachment_name"), task.get("attachment_path"), task.get("attachment_type"), now, now),
		)
		task_id = _inserted_id(cursor.fetchone())
		cursor.close()
	return get_task(database_path, task_id)


def update_task(database_path, task_id, values):
	allowed = {"title", "course", "description", "deadline", "difficulty", "completed"}
	changes = {key: value for key, value in values.items() if key in allowed}
	if not changes:
		return get_task(database_path, task_id)
	changes["updated_at"] = datetime.now(timezone.utc).isoformat()
	set_clause = ", ".join(f"{key} = ?" for key in changes)
	with get_connection(database_path) as connection:
		connection.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", [*changes.values(), task_id])
	return get_task(database_path, task_id)


def delete_task(database_path, task_id):
	with get_connection(database_path) as connection:
		connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


def _note_with_attachments(connection, note):
	result = _row_to_dict(note)
	if not result:
		return None
	result["caption"] = sanitize_rich_text(result.get("caption"))
	result["attachments"] = [
		_row_to_dict(attachment)
		for attachment in connection.execute(
			"SELECT id, name, path, type, created_at FROM note_attachments WHERE note_id = ? ORDER BY id",
			(result["id"],),
		).fetchall()
	]
	return result


def list_notes(database_path, course=""):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM notes"
		params = []
		if course:
			query += " WHERE course = ?"
			params.append(course)
		query += " ORDER BY created_at DESC, id DESC"
		return [_note_with_attachments(connection, row) for row in connection.execute(query, params).fetchall()]


def get_note(database_path, note_id):
	with get_connection(database_path) as connection:
		return _note_with_attachments(connection, connection.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone())


def add_note(database_path, note):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"INSERT INTO notes (title, course, caption, attachment_name, attachment_path, attachment_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
			(note["title"], note["course"], note["caption"], None, None, None, now, now),
		)
		note_id = _inserted_id(cursor.fetchone())
		for attachment in note.get("attachments", []):
			connection.execute(
				"INSERT INTO note_attachments (note_id, name, path, type, created_at) VALUES (?, ?, ?, ?, ?)",
				(note_id, attachment["name"], attachment["path"], attachment["type"], now),
			)
	return get_note(database_path, note_id)


def update_note(database_path, note_id, values):
	allowed = {"title", "course", "caption"}
	changes = {key: value for key, value in values.items() if key in allowed}
	if not changes:
		return get_note(database_path, note_id)
	changes["updated_at"] = datetime.now(timezone.utc).isoformat()
	set_clause = ", ".join(f"{key} = ?" for key in changes)
	with get_connection(database_path) as connection:
		connection.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", [*changes.values(), note_id])
	return get_note(database_path, note_id)


def add_note_attachments(database_path, note_id, attachments):
	if not attachments:
		return get_note(database_path, note_id)
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		for attachment in attachments:
			connection.execute(
				"INSERT INTO note_attachments (note_id, name, path, type, created_at) VALUES (?, ?, ?, ?, ?)",
				(note_id, attachment["name"], attachment["path"], attachment["type"], now),
			)
	return get_note(database_path, note_id)


def delete_note(database_path, note_id):
	with get_connection(database_path) as connection:
		connection.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def list_wallets(database_path, active_only=False):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM wallets"
		if active_only:
			query += " WHERE active = 1"
		query += " ORDER BY CASE WHEN course IS NULL THEN 1 ELSE 0 END, name"
		return [_row_to_dict(row) for row in connection.execute(query).fetchall()]


def get_wallet(database_path, wallet_id):
	with get_connection(database_path) as connection:
		return _row_to_dict(connection.execute("SELECT * FROM wallets WHERE id = ?", (wallet_id,)).fetchone())


def add_wallet(database_path, wallet):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute("INSERT INTO wallets (name, course, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?) RETURNING id", (wallet["name"], wallet.get("course"), wallet.get("active", 1), now, now))
		wallet_id = _inserted_id(cursor.fetchone())
		cursor.close()
	return get_wallet(database_path, wallet_id)


def list_contributors(database_path, active_only=False):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM contributors"
		if active_only:
			query += " WHERE active = 1"
		query += " ORDER BY name"
		return [_row_to_dict(row) for row in connection.execute(query).fetchall()]


def add_contributor(database_path, name):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute("INSERT INTO contributors (name, created_at, updated_at) VALUES (?, ?, ?) RETURNING id", (name, now, now))
		contributor_id = _inserted_id(cursor.fetchone())
		cursor.close()
		return _row_to_dict(connection.execute("SELECT * FROM contributors WHERE id = ?", (contributor_id,)).fetchone())


def list_budget_entries(database_path, wallet_id=None):
	with get_connection(database_path) as connection:
		query = "SELECT budget_entries.*, wallets.name AS wallet_name, contributors.name AS contributor_name FROM budget_entries LEFT JOIN wallets ON wallets.id = budget_entries.wallet_id LEFT JOIN contributors ON contributors.id = budget_entries.contributor_id"
		params = []
		if wallet_id:
			query += " WHERE budget_entries.wallet_id = ?"
			params.append(wallet_id)
		query += " ORDER BY budget_entries.created_at DESC, budget_entries.id DESC"
		rows = connection.execute(query, params).fetchall()
		return [_row_to_dict(row) for row in rows]


def add_budget_entry(database_path, entry):
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"INSERT INTO budget_entries (type, amount, reason, status, wallet_id, course, contributor_id, attachment_name, attachment_path, attachment_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
			(entry["type"], entry["amount"], entry["reason"], entry.get("status", "pending"), entry.get("wallet_id"), entry.get("course"), entry.get("contributor_id"), entry.get("attachment_name"), entry.get("attachment_path"), entry.get("attachment_type"), datetime.now(timezone.utc).isoformat()),
		)
		entry_id = _inserted_id(cursor.fetchone())
		cursor.close()
		row = connection.execute("SELECT * FROM budget_entries WHERE id = ?", (entry_id,)).fetchone()
		connection.execute("INSERT INTO budget_audit_events (entry_id, event_type, actor, payload, created_at) VALUES (?, ?, ?, ?, ?)", (entry_id, "created", entry.get("actor", "system"), json.dumps({"type": entry["type"], "amount": entry["amount"], "wallet_id": entry.get("wallet_id")}), datetime.now(timezone.utc).isoformat()))
	return _row_to_dict(row)


def update_budget_entry(database_path, entry_id, values):
	allowed = {"type", "status", "reason", "contributor_id", "wallet_id", "course"}
	changes = {key: value for key, value in values.items() if key in allowed}
	if not changes:
		return get_budget_entry(database_path, entry_id)
	set_clause = ", ".join(f"{key} = ?" for key in changes)
	with get_connection(database_path) as connection:
		connection.execute(f"UPDATE budget_entries SET {set_clause} WHERE id = ?", [*changes.values(), entry_id])
		connection.execute("INSERT INTO budget_audit_events (entry_id, event_type, actor, payload, created_at) VALUES (?, ?, ?, ?, ?)", (entry_id, "updated", values.get("actor", "system"), json.dumps(changes), datetime.now(timezone.utc).isoformat()))
	return get_budget_entry(database_path, entry_id)


def list_budget_audit_events(database_path, entry_id=None):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM budget_audit_events"
		params = []
		if entry_id:
			query += " WHERE entry_id = ?"
			params.append(entry_id)
		query += " ORDER BY created_at DESC, id DESC"
		return [_row_to_dict(row) for row in connection.execute(query, params).fetchall()]


def get_budget_entry(database_path, entry_id):
	with get_connection(database_path) as connection:
		return _row_to_dict(connection.execute("SELECT * FROM budget_entries WHERE id = ?", (entry_id,)).fetchone())


def _announcement_with_options(connection, announcement):
	result = _row_to_dict(announcement)
	if not result:
		return None
	result["body"] = sanitize_rich_text(result.get("body"))
	result["options"] = [
		_row_to_dict(row)
		for row in connection.execute(
			"""
			SELECT o.id, o.label, o.position, COUNT(v.id) AS votes
			FROM poll_options o
			LEFT JOIN poll_votes v ON v.option_id = o.id
			WHERE o.announcement_id = ?
			GROUP BY o.id
			ORDER BY o.position, o.id
			""",
			(result["id"],),
		).fetchall()
	]
	return result


def list_announcements(database_path, limit=None):
	with get_connection(database_path) as connection:
		query = "SELECT * FROM announcements ORDER BY created_at DESC, id DESC"
		params = ()
		if limit is not None:
			query += " LIMIT ?"
			params = (limit,)
		return [_announcement_with_options(connection, row) for row in connection.execute(query, params).fetchall()]


def search_content(database_path, term, limit=12, course="", kind=""):
	pattern = f"%{term}%"
	course_pattern = f"%{course}%"
	with get_connection(database_path) as connection:
		params = [pattern, pattern, pattern]
		task_query = """
			SELECT id, title, description AS detail, course AS meta, created_at
			FROM tasks
			WHERE (title LIKE ? OR description LIKE ? OR course LIKE ?)
		"""
		if course:
			task_query += " AND course LIKE ?"
			params.append(course_pattern)
		task_query += " ORDER BY created_at DESC, id DESC LIMIT ?"
		params.append(limit)
		tasks = connection.execute(task_query, params).fetchall()
		announcement_params = [pattern, pattern]
		announcement_query = """
			SELECT id, title, body AS detail, 'Announcement' AS meta, created_at
			FROM announcements
			WHERE (title LIKE ? OR body LIKE ?)
		"""
		if course:
			announcement_query += " AND body LIKE ?"
			announcement_params.append(course_pattern)
		announcement_query += " ORDER BY created_at DESC, id DESC LIMIT ?"
		announcement_params.append(limit)
		announcements = connection.execute(announcement_query, announcement_params).fetchall()
		note_params = [pattern, pattern, pattern]
		note_query = """
			SELECT id, title, caption AS detail, course AS meta, created_at
			FROM notes
			WHERE (title LIKE ? OR caption LIKE ? OR course LIKE ?)
		"""
		if course:
			note_query += " AND course LIKE ?"
			note_params.append(course_pattern)
		note_query += " ORDER BY created_at DESC, id DESC LIMIT ?"
		note_params.append(limit)
		notes = connection.execute(note_query, note_params).fetchall()
	results = []
	if kind in ("", "Task"):
		results.extend({**_row_to_dict(row), "kind": "Task", "url": "/tasks"} for row in tasks)
	if kind in ("", "Announcement"):
		results.extend({**_row_to_dict(row), "kind": "Announcement", "url": f"/announcements#announcement-{row['id']}"} for row in announcements)
	if kind in ("", "Note"):
		results.extend({**_row_to_dict(row), "kind": "Note", "url": f"/notes#note-{row['id']}"} for row in notes)
	for result in results:
		plain_detail = rich_text_plain(result.get("detail") or "")
		text = f"{result['title']} {plain_detail} {result.get('meta') or ''}".lower()
		term_lower = term.lower()
		result["score"] = (text.count(term_lower) * 3) + (result["title"].lower().count(term_lower) * 5)
		result["snippet"] = plain_detail[:180]
	return sorted(results, key=lambda item: (item["score"], item["created_at"], item["id"]), reverse=True)[:limit]


def add_announcement(database_path, announcement, options=None):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"""
			INSERT INTO announcements
			(title, body, link_url, attachment_name, attachment_path, attachment_type, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id
			""",
			(
				announcement["title"],
				announcement["body"],
				announcement.get("link_url"),
				announcement.get("attachment_name"),
				announcement.get("attachment_path"),
				announcement.get("attachment_type"),
				now,
				now,
			),
		)
		announcement_id = _inserted_id(cursor.fetchone())
		for position, label in enumerate(options or []):
			connection.execute(
				"INSERT INTO poll_options (announcement_id, label, position) VALUES (?, ?, ?)",
				(announcement_id, label, position),
			)
		row = connection.execute("SELECT * FROM announcements WHERE id = ?", (announcement_id,)).fetchone()
		return _announcement_with_options(connection, row)


def add_poll_vote(database_path, announcement_id, option_id, school_id):
	with get_connection(database_path) as connection:
		option = connection.execute(
			"SELECT id FROM poll_options WHERE id = ? AND announcement_id = ?",
			(option_id, announcement_id),
		).fetchone()
		if not option:
			return None
		connection.execute(
			"INSERT INTO poll_votes (announcement_id, option_id, school_id, created_at) VALUES (?, ?, ?, ?)",
			(announcement_id, option_id, school_id, datetime.now(timezone.utc).isoformat()),
		)
		row = connection.execute("SELECT * FROM announcements WHERE id = ?", (announcement_id,)).fetchone()
		return _announcement_with_options(connection, row)


def list_no_class_exceptions(database_path, target_date=None):
	with get_connection(database_path) as connection:
		if target_date:
			rows = connection.execute("SELECT * FROM no_class_exceptions WHERE date = ? ORDER BY course", (target_date,)).fetchall()
		else:
			rows = connection.execute("SELECT * FROM no_class_exceptions ORDER BY date DESC, course").fetchall()
		return [_row_to_dict(row) for row in rows]


def add_no_class_exception(database_path, target_date, course):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		existing = connection.execute(
			"SELECT id FROM no_class_exceptions WHERE date = ? AND course = ?", (target_date, course)
		).fetchone()
		if existing:
			return _row_to_dict(connection.execute("SELECT * FROM no_class_exceptions WHERE id = ?", (_inserted_id(existing),)).fetchone())
		cursor = connection.execute(
			"INSERT INTO no_class_exceptions (date, course, created_at) VALUES (?, ?, ?) RETURNING id",
			(target_date, course, now),
		)
		exception_id = _inserted_id(cursor.fetchone())
		cursor.close()
		return _row_to_dict(connection.execute("SELECT * FROM no_class_exceptions WHERE id = ?", (exception_id,)).fetchone())


def delete_no_class_exception(database_path, exception_id):
	with get_connection(database_path) as connection:
		row = connection.execute("SELECT * FROM no_class_exceptions WHERE id = ?", (exception_id,)).fetchone()
		if not row:
			return None
		connection.execute("DELETE FROM no_class_exceptions WHERE id = ?", (exception_id,))
		return _row_to_dict(row)
