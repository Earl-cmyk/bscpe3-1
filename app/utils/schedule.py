"""Canonical weekly class schedule and helpers.

Schedule data is static and read-only — it never touches the database.
"""

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

MANILA = ZoneInfo("Asia/Manila")

# Each entry: (weekday 0=Mon..6=Sun, start, end, course_title)
WEEKLY_SCHEDULE = [
	# Monday
	{"day": 0, "start": time(13, 30), "end": time(16, 0), "course": "Predictive Analytics Modelling, Simulation and \u2026"},
	{"day": 0, "start": time(18, 0), "end": time(21, 0), "course": "Introduction Hardware Descriptive Language"},
	# Tuesday
	{"day": 1, "start": time(7, 30), "end": time(9, 0), "course": "Data and Digital Communications"},
	{"day": 1, "start": time(10, 30), "end": time(13, 30), "course": "Logic Circuits and Design"},
	# Wednesday
	{"day": 2, "start": time(13, 30), "end": time(16, 0), "course": "Predictive Analytics Modelling, Simulation and \u2026"},
	{"day": 2, "start": time(18, 0), "end": time(21, 0), "course": "Fundamentals of Mixed Signals and Sensors"},
	# Thursday — no class
	# Friday
	{"day": 4, "start": time(7, 30), "end": time(9, 0), "course": "Data and Digital Communications"},
	{"day": 4, "start": time(10, 30), "end": time(13, 30), "course": "Logic Circuits and Design"},
	{"day": 4, "start": time(13, 30), "end": time(16, 0), "course": "Engineering Economics"},
	# Saturday
	{"day": 5, "start": time(10, 30), "end": time(13, 30), "course": "Technical Writing"},
	{"day": 5, "start": time(14, 0), "end": time(17, 0), "course": "Data and Digital Communications"},
	{"day": 5, "start": time(18, 0), "end": time(21, 0), "course": "Computer Engineering Drafting and Design"},
	# Sunday — no class
]

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Maps full schedule course titles to the short codes used in tasks/deadlines
COURSE_SHORT = {
	"Introduction Hardware Descriptive Language": "HDL",
	"Logic Circuits and Design": "LCD",
	"Data and Digital Communications": "DDC",
	"Computer Engineering Drafting and Design": "CEDD",
	"Fundamentals of Mixed Signals and Sensors": "FOSS",
	"Technical Writing": "TRW",
	"Engineering Economics": "Engr Econ",
	"Predictive Analytics Modelling, Simulation and \u2026": "Elec",
}


def get_schedule_for_weekday(weekday):
	"""Return schedule entries for a weekday (0=Monday .. 6=Sunday)."""
	return [entry for entry in WEEKLY_SCHEDULE if entry["day"] == weekday]


def get_schedule_for_date(target_date, exceptions=None):
	"""Return schedule entries for a calendar date, filtering out exceptions.

	*exceptions* is an iterable of dicts with ``course`` keys that have been
	cancelled on this specific date.
	"""
	entries = get_schedule_for_weekday(target_date.weekday())
	if exceptions:
		cancelled = {exc["course"] for exc in exceptions}
		cancelled_titles = {course for course, short in COURSE_SHORT.items() if short in cancelled}
		entries = [e for e in entries if e["course"] not in cancelled and e["course"] not in cancelled_titles]
	return entries


def today_manila():
	return datetime.now(timezone.utc).astimezone(MANILA).date()


def parse_manila_datetime(value):
	"""Parse ISO or common conversational datetime values in Manila."""
	text = str(value or "").strip()
	try:
		parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
	except ValueError:
		match = re.fullmatch(r"(today|tomorrow|[A-Za-z]+)\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.I)
		if not match:
			raise ValueError("Invalid date and time")
		day_text, hour_text, minute_text, meridiem = match.groups()
		target_date = today_manila()
		if day_text.casefold() == "tomorrow":
			target_date += timedelta(days=1)
		elif day_text.casefold() not in {"today", "tomorrow"}:
			weekday = next((index for index, name in enumerate(DAY_NAMES) if name.casefold().startswith(day_text.casefold())), None)
			if weekday is None:
				raise ValueError("Invalid date and time")
			target_date += timedelta(days=(weekday - target_date.weekday()) % 7)
		hour = int(hour_text)
		minute = int(minute_text or 0)
		if meridiem:
			if hour < 1 or hour > 12:
				raise ValueError("Invalid date and time")
			if meridiem.casefold() == "pm" and hour != 12:
				hour += 12
			elif meridiem.casefold() == "am" and hour == 12:
				hour = 0
		if minute > 59 or hour > 23:
			raise ValueError("Invalid date and time")
		parsed = datetime.combine(target_date, time(hour, minute))
	if parsed.tzinfo is None:
		parsed = parsed.replace(tzinfo=MANILA)
	return parsed.astimezone(timezone.utc).isoformat()


def parse_manila_date(value):
	text = str(value or "").strip()
	try:
		return date.fromisoformat(text)
	except ValueError:
		lowered = text.casefold()
		today = today_manila()
		if lowered == "today":
			return today
		if lowered == "tomorrow":
			return today + timedelta(days=1)
		weekday = next((index for index, name in enumerate(DAY_NAMES) if name.casefold().startswith(lowered)), None)
		if weekday is not None:
			return today + timedelta(days=(weekday - today.weekday()) % 7)
		for pattern in ("%B %d, %Y", "%b %d, %Y"):
			try:
				return datetime.strptime(text, pattern).date()
			except ValueError:
				continue
		raise ValueError("Invalid date")


def serialize_entry(entry):
	"""Convert a schedule entry to a JSON-safe dict."""
	return {
		"day": entry["day"],
		"day_name": DAY_NAMES[entry["day"]],
		"start": entry["start"].strftime("%I:%M %p").lstrip("0"),
		"end": entry["end"].strftime("%I:%M %p").lstrip("0"),
		"start_minutes": entry["start"].hour * 60 + entry["start"].minute,
		"end_minutes": entry["end"].hour * 60 + entry["end"].minute,
		"course": entry["course"],
		"short": COURSE_SHORT.get(entry["course"], ""),
	}
