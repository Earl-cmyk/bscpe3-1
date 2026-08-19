from calendar import monthrange
from datetime import date, datetime, timedelta, timezone


def parse_deadline(value):
	parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
	if parsed.tzinfo is None:
		parsed = parsed.replace(tzinfo=timezone.utc)
	return parsed.astimezone(timezone.utc)


def day_bounds(target):
	start = datetime.combine(target, datetime.min.time(), timezone.utc)
	return start, start + timedelta(days=1)


def week_bounds(target):
	start_date = target - timedelta(days=target.weekday())
	start = datetime.combine(start_date, datetime.min.time(), timezone.utc)
	return start, start + timedelta(days=7)


def month_bounds(year, month):
	start = datetime(year, month, 1, tzinfo=timezone.utc)
	return start, datetime(year + (month == 12), 1 if month == 12 else month + 1, 1, tzinfo=timezone.utc)


def calendar_payload(tasks, selected_date):
	start, end = month_bounds(selected_date.year, selected_date.month)
	first_cell = start - timedelta(days=start.weekday())
	last_day = end - timedelta(days=1)
	last_cell = last_day + timedelta(days=6 - last_day.weekday())
	task_map = {}
	for task in tasks:
		try:
			day = parse_deadline(task["deadline"]).date().isoformat()
		except (KeyError, TypeError, ValueError):
			continue
		task_map.setdefault(day, []).append(task)
	return {
		"month": start.strftime("%Y-%m"),
		"start": first_cell.date().isoformat(),
		"end": last_cell.date().isoformat(),
		"days": task_map,
	}
