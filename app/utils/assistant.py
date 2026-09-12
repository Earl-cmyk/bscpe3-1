import re
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .rich_text import rich_text_plain
from .schedule import today_manila
from .study import compose_study_response, study_mode
from ..services.earllm_client import EarllmError, EarllmInvalidResponse, EarllmUnavailable, predict
from ..services.posts.simple_interest import SimpleInterestError, solve_simple_interest_problem

NO_NOTE_CONTEXT = "I couldn't find information about that in your Notes."
NOTE_CONTEXT_UNAVAILABLE = "I couldn't access your Notes right now. Please try again later."
logger = logging.getLogger(__name__)


def classify_message(message, nlu_result=None, nlu_url=None, nlu_timeout=None):
	text = " ".join(str(message or "").split())
	if not text:
		return {"intent": "clarification", "message": "Tell me what you need help with."}
	if nlu_result is None:
		if not nlu_url:
			raise EarllmUnavailable("NLU service is not configured")
		nlu_result = predict(text, nlu_url, nlu_timeout)
	return _route_prediction(nlu_result, text)


def answer_message(database_path, message, nlu_url=None, nlu_timeout=None):
	try:
		route = classify_message(message, nlu_url=nlu_url, nlu_timeout=nlu_timeout)
	except EarllmUnavailable:
		return {"intent": "unavailable", "message": "Rein's local language service is unavailable right now. Please try again later."}
	except (EarllmInvalidResponse, EarllmError):
		return {"intent": "clarification", "message": "I couldn't safely understand that request. Please rephrase it."}
	if route.get("confidence_band") == "clarification_required" or route.get("confidence", 1) < 0.60:
		return {**route, "intent": "clarification", "message": "I'm not quite sure what you want Rein to do. Could you rephrase that?"}
	if route["intent"] == "mastercontrol_action":
		return {**route, "message": "I parsed this as a Mastercontrol action. PIN authorization and confirmation are required before anything changes."}
	if route["intent"] == "note_query":
		from ..models import search_interactive_context, search_note_context

		try:
			course = route.get("course", "")
			matches = search_note_context(database_path, route["query"], course=course)
			matches += search_interactive_context(database_path, route["query"], course=course)
		except Exception:
			logger.exception("Note retrieval failed for assistant query")
			return {**route, "message": NOTE_CONTEXT_UNAVAILABLE, "sources": []}
		if not matches:
			return {**route, "message": NO_NOTE_CONTEXT, "sources": []}
		study = compose_study_response(route["query"], matches, route.get("mode", study_mode(message)))
		return {**route, **study}
	if route["intent"] == "simple_interest":
		try:
			result = solve_simple_interest_problem(message)
		except SimpleInterestError as error:
			return {**route, "message": str(error)}
		return {**route, "message": "\n".join(result["steps"]), "calculation": result}
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


def _route_prediction(prediction, text):
	intent = prediction["intent"]
	entities = prediction["entities"]
	result = {"intent": intent, "confidence": prediction["confidence"], "confidence_band": prediction["confidence_band"], "entities": entities}
	if intent in {"GET_SCHEDULE", "GET_TODAY_SCHEDULE", "GET_TOMORROW_SCHEDULE"} and _is_learning_request(text):
		return {**result, "intent": "note_query", "query": entities.get("topic") or text, "course": ""}
	date_text = entities.get("date") or _relative_date(text.casefold()).isoformat()
	course = _course_entity(entities.get("course"))
	if intent == "CREATE_DEADLINE":
		missing = _missing(entities, "course", "date", "time", "title")
		if missing or not _valid_course(course):
			return {**result, "intent": "clarification", "message": "Sure. What course, title, due date, and time should I use?"}
		return {**result, "intent": "mastercontrol_action", "tool": "create_deadline", "arguments": _deadline_arguments(entities, course)}
	if intent == "MARK_NO_CLASS":
		if _missing(entities, "course", "date") or not _valid_course(course):
			return {**result, "intent": "clarification", "message": "Which course and date should I mark as having no class?"}
		return {**result, "intent": "mastercontrol_action", "tool": "add_no_class_exception", "arguments": {"course": course, "date": date_text}}
	if intent == "DELETE_DEADLINE":
		if _missing(entities, "deadline_id"):
			return {**result, "intent": "clarification", "message": "Which deadline should I remove?"}
		return {**result, "intent": "mastercontrol_action", "tool": "delete_deadline", "arguments": {"deadline_id": entities.get("deadline_id")}}
	if intent in {"RECORD_DEPOSIT", "RECORD_EXPENSE"}:
		course = course or _course_in(text)
		if _missing(entities, "amount") or not _valid_course(course):
			return {**result, "intent": "clarification", "message": "What amount and course wallet should I use, and what is it for?"}
		return {**result, "intent": "mastercontrol_action", "tool": "record_transaction", "arguments": {"type": "deposit" if intent == "RECORD_DEPOSIT" else "withdraw", "amount": entities.get("amount"), "course": course, "reason": entities.get("description") or entities.get("topic") or _transaction_reason(text)}}
	if intent in {"LEARN_TOPIC", "SEARCH_NOTES", "EXPLAIN_TOPIC", "PRACTICE_TOPIC", "QUIZ_TOPIC"}:
		mode = {"EXPLAIN_TOPIC": "explain", "PRACTICE_TOPIC": "practice", "QUIZ_TOPIC": "quiz"}.get(intent, study_mode(text))
		return {**result, "intent": "note_query", "query": entities.get("topic") or _note_query(text), "course": course or "", "mode": mode}
	if intent == "SIMPLE_INTEREST":
		return {**result, "intent": "simple_interest"}
	if intent in {"GET_SCHEDULE", "GET_TODAY_SCHEDULE", "GET_TOMORROW_SCHEDULE"}:
		target = "today" if intent == "GET_TODAY_SCHEDULE" else "tomorrow" if intent == "GET_TOMORROW_SCHEDULE" else date_text
		return {**result, "intent": "schedule", "date": _resolve_date(target)}
	if intent in {"GET_DEADLINES", "GET_COURSE_DEADLINES", "GET_WEEK_DEADLINES"}:
		target = _resolve_date(date_text)
		return {**result, "intent": "deadlines", "start": target, "course": course or ""}
	if intent in {"GET_ANNOUNCEMENTS", "GET_POLLS", "GET_FUND_BALANCE", "GET_FUND_TRANSACTIONS", "CREATE_ANNOUNCEMENT", "CREATE_POLL", "UPDATE_DEADLINE", "DELETE_NOTE", "UPDATE_NOTE", "VOTE_POLL"}:
		return {**result, "intent": "unsupported", "message": "Rein understands that request, but that function isn't available yet."}
	return {**result, "intent": "clarification", "message": "I'm not quite sure what you want Rein to do. Could you rephrase that?"}


def _deadline_arguments(entities, course):
	date_text = entities.get("date")
	time_text = entities.get("time")
	when = " ".join(value for value in (date_text, time_text) if value)
	return {"datetime": when, "course": course, "title": entities.get("title"), "description": entities.get("description") or entities.get("title"), "difficulty": "Medium"}


def _course_entity(value):
	if not value:
		return ""
	from ..utils.mastercontrol import _course

	try:
		return _course(value)
	except ValueError:
		return str(value).strip()

def _valid_course(value):
	from config import ALLOWED_COURSES

	return value in ALLOWED_COURSES


def _missing(entities, *names):
	return any(entities.get(name) in (None, "", []) for name in names)


def _is_learning_request(text):
	educational = bool(re.search(r"\b(?:teach|explain|learn|solve|calculate|find)\b", text, re.I))
	explicitly_not_schedule = bool(re.search(r"\bnot\s+(?:my\s+)?(?:schedule|class(?:es)?|timetable)\b", text, re.I))
	has_schedule_context = bool(re.search(r"\b(?:schedule|class(?:es)?|timetable)\b", text, re.I))
	return educational and (explicitly_not_schedule or not has_schedule_context)


def _transaction_reason(text):
	match = re.search(r"\bfor\s+.+?\s+for\s+(.+)$", text, re.I)
	return match.group(1).strip(" .?!") if match else text

def _resolve_date(value):
	from .schedule import parse_manila_date

	try:
		return parse_manila_date(value)
	except ValueError:
		return value


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