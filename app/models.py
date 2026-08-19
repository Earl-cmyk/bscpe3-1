import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager


@contextmanager
def get_connection(database_path):
	connection = sqlite3.connect(database_path)
	connection.row_factory = sqlite3.Row
	try:
		yield connection
		connection.commit()
	except Exception:
		connection.rollback()
		raise
	finally:
		connection.close()


def init_db(database_path):
	with get_connection(database_path) as connection:
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
		budget_columns = {row["name"] for row in connection.execute("PRAGMA table_info(budget_entries)").fetchall()}
		if "status" not in budget_columns:
			connection.execute("ALTER TABLE budget_entries ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")
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


def get_task(database_path, task_id):
	with get_connection(database_path) as connection:
		return _row_to_dict(connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def add_task(database_path, task):
	now = datetime.now(timezone.utc).isoformat()
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"INSERT INTO tasks (title, course, description, deadline, difficulty, attachment_name, attachment_path, attachment_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
			(task["title"], task["course"], task["description"], task["deadline"], task["difficulty"], task.get("attachment_name"), task.get("attachment_path"), task.get("attachment_type"), now, now),
		)
	return get_task(database_path, cursor.lastrowid)


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


def list_budget_entries(database_path):
	with get_connection(database_path) as connection:
		rows = connection.execute("SELECT * FROM budget_entries ORDER BY created_at DESC, id DESC").fetchall()
		return [_row_to_dict(row) for row in rows]


def add_budget_entry(database_path, entry):
	with get_connection(database_path) as connection:
		cursor = connection.execute(
			"INSERT INTO budget_entries (type, amount, reason, status, created_at) VALUES (?, ?, ?, ?, ?)",
			(entry["type"], entry["amount"], entry["reason"], entry.get("status", "pending"), datetime.now(timezone.utc).isoformat()),
		)
		row = connection.execute("SELECT * FROM budget_entries WHERE id = ?", (cursor.lastrowid,)).fetchone()
	return _row_to_dict(row)


def update_budget_entry(database_path, entry_id, values):
	allowed = {"type", "status"}
	changes = {key: value for key, value in values.items() if key in allowed}
	if not changes:
		return get_budget_entry(database_path, entry_id)
	set_clause = ", ".join(f"{key} = ?" for key in changes)
	with get_connection(database_path) as connection:
		connection.execute(f"UPDATE budget_entries SET {set_clause} WHERE id = ?", [*changes.values(), entry_id])
	return get_budget_entry(database_path, entry_id)


def get_budget_entry(database_path, entry_id):
	with get_connection(database_path) as connection:
		return _row_to_dict(connection.execute("SELECT * FROM budget_entries WHERE id = ?", (entry_id,)).fetchone())
