import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EarllmError(Exception):
	"""Raised when the local NLU service cannot provide a safe prediction."""


class EarllmUnavailable(EarllmError):
	pass


class EarllmInvalidResponse(EarllmError):
	pass


ALLOWED_BANDS = {"high", "possible_ambiguity", "clarification_required"}
MAX_TEXT_LENGTH = 2000
MAX_ENTITY_LENGTH = 500


def predict(text, base_url, timeout):
	text = " ".join(str(text or "").split())
	if not text:
		raise EarllmInvalidResponse("Empty text")
	if len(text) > MAX_TEXT_LENGTH:
		raise EarllmInvalidResponse("Text is too long")
	body = json.dumps({"text": text}).encode("utf-8")
	request = Request(
		base_url.rstrip("/") + "/predict",
		data=body,
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	try:
		with urlopen(request, timeout=float(timeout)) as response:
			payload = json.loads(response.read().decode("utf-8"))
	except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as error:
		raise EarllmUnavailable("NLU service unavailable") from error
	return validate_prediction(payload)


def validate_prediction(payload):
	if not isinstance(payload, dict):
		raise EarllmInvalidResponse("Prediction must be an object")
	intent = payload.get("intent")
	if not isinstance(intent, str) or not intent.strip():
		raise EarllmInvalidResponse("Prediction intent is missing")
	try:
		confidence = float(payload.get("confidence"))
	except (TypeError, ValueError):
		raise EarllmInvalidResponse("Prediction confidence is invalid")
	if not 0 <= confidence <= 1:
		raise EarllmInvalidResponse("Prediction confidence is out of range")
	band = payload.get("confidence_band")
	if not isinstance(band, str) or band.casefold() not in ALLOWED_BANDS:
		raise EarllmInvalidResponse("Prediction confidence band is invalid")
	entities = payload.get("entities", {})
	if not isinstance(entities, dict):
		raise EarllmInvalidResponse("Prediction entities are invalid")
	for key, value in entities.items():
		if isinstance(value, str) and len(value) > MAX_ENTITY_LENGTH:
			raise EarllmInvalidResponse("Prediction entity is too long")
		if key.endswith("_id"):
			try:
				if int(value) < 1:
					raise ValueError
			except (TypeError, ValueError):
				raise EarllmInvalidResponse("Prediction ID is invalid")
		if key == "amount":
			try:
				if Decimal(str(value)) <= 0:
					raise ValueError
			except (InvalidOperation, TypeError, ValueError):
				raise EarllmInvalidResponse("Prediction amount is invalid")
	return {
		"intent": intent.strip().upper(),
		"confidence": confidence,
		"confidence_band": band.casefold(),
		"entities": dict(entities),
	}
