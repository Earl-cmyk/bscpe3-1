import re
from datetime import date, timedelta


COURSE_PATTERN = r"HDL|LCD|DDC|CEDD|FOSS|TRW|Elec|Engr Econ"


def parse_query(query, today=None):
	query = " ".join(query.strip().split())
	today = today or date.today()
	lower = query.lower()
	if lower == "deadlines today":
		return {"label": "Due today", "start": today, "end": today}
	if lower == "deadlines this week":
		return {"label": "Due this week", "start": today - timedelta(days=today.weekday()), "end": today + timedelta(days=6 - today.weekday())}
	if lower == "deadlines this month":
		return {"label": "Due this month", "start": today.replace(day=1), "end": today.replace(day=28) + timedelta(days=4)}
	course_match = re.search(rf"to do for ({COURSE_PATTERN})\b", query, re.IGNORECASE)
	if not course_match:
		return None
	course = course_match.group(1)
	date_match = re.search(r"on (\d{4}-\d{2}-\d{2})", lower)
	range_match = re.search(r"from (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})", lower)
	try:
		if range_match:
			start, end = date.fromisoformat(range_match.group(1)), date.fromisoformat(range_match.group(2))
		elif date_match:
			start = end = date.fromisoformat(date_match.group(1))
		elif "today" in lower:
			start = end = today
		else:
			return None
	except ValueError:
		return None
	return {"label": f"{course} tasks", "course": course, "start": start, "end": end}
