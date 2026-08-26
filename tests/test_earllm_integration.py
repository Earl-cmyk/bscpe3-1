import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.models import get_connection, init_db, list_tasks, search_note_context
from app.services.earllm_client import EarllmInvalidResponse, validate_prediction
from app.utils.assistant import answer_message, classify_message


class EarllmIntegrationTests(unittest.TestCase):
	def setUp(self):
		self.temp_dir = tempfile.TemporaryDirectory()
		self.database_path = str(Path(self.temp_dir.name) / "test.db")
		with patch("app.DATABASE_URL", ""), patch("app.DATABASE_PATH", Path(self.database_path)):
			self.app = create_app()
		self.app.config.update(TESTING=True, DATABASE_PATH=self.database_path, TASK_PIN="123456")
		self.client = self.app.test_client()

	def tearDown(self):
		self.temp_dir.cleanup()

	def test_required_prediction_mappings(self):
		cases = [
			("Can you mark LCD as having no class tomorrow?", {"intent": "MARK_NO_CLASS", "entities": {"course": "LCD", "date": "tomorrow"}}, "add_no_class_exception"),
			("Please add a deadline for my HDL class tomorrow at 6 PM titled lab report.", {"intent": "CREATE_DEADLINE", "entities": {"course": "HDL", "date": "tomorrow", "time": "18:00", "title": "lab report"}}, "create_deadline"),
			("Record a 500 peso deposit for HDL for printing materials.", {"intent": "RECORD_DEPOSIT", "entities": {"amount": 500}}, "record_transaction"),
			("Could you remove deadline 7?", {"intent": "DELETE_DEADLINE", "entities": {"deadline_id": 7}}, "delete_deadline"),
		]
		for text, data, tool in cases:
			prediction = {**data, "confidence": 0.99, "confidence_band": "high"}
			result = classify_message(text, nlu_result=prediction)
			self.assertEqual(result["tool"], tool)
			if tool == "record_transaction":
				self.assertEqual(result["arguments"].get("course"), "HDL")
				self.assertEqual(result["arguments"].get("reason"), "printing materials")

		learning = classify_message(
			"Rein, how do I use 3's complement?",
			nlu_result={"intent": "LEARN_TOPIC", "confidence": 0.99, "confidence_band": "high", "entities": {"topic": "3's complement"}},
		)
		self.assertEqual(learning["intent"], "note_query")
		self.assertEqual(learning["query"], "3's complement")

	def test_missing_entities_require_clarification(self):
		result = classify_message(
			"Add a deadline.",
			nlu_result={"intent": "CREATE_DEADLINE", "confidence": 0.99, "confidence_band": "high", "entities": {}},
		)
		self.assertEqual(result["intent"], "clarification")
		self.assertNotIn("tool", result)

	def test_note_grounding_returns_no_context(self):
		with patch("app.utils.assistant.predict", return_value={"intent": "LEARN_TOPIC", "confidence": 0.99, "confidence_band": "high", "entities": {"topic": "nonexistent topic"}}):
			result = answer_message(self.database_path, "How does nonexistent topic work?", "http://nlu", 1)
		self.assertEqual(result["message"], "I couldn't find information about that in your Notes.")
		self.assertEqual(result["sources"], [])

	def test_note_context_uses_postgres_search_without_sqlite_fts(self):
		class FakeResult:
			def __init__(self, rows):
				self.rows = rows

			def fetchall(self):
				return self.rows

		class FakeConnection:
			def __init__(self):
				self.query = ""
				self.calls = 0

			def execute(self, query, params=()):
				self.query = query
				self.calls += 1
				if self.calls == 1:
					return FakeResult([])
				return FakeResult([{"note_id": 4, "title": "Binary arithmetic", "course": "HDL", "content": "Learn complements."}])

		fake_connection = FakeConnection()
		with patch("app.models.get_connection") as get_connection_mock:
			get_connection_mock.return_value.__enter__.return_value = fake_connection
			result = search_note_context("postgresql://database", "complements", course="HDL")
		self.assertEqual(result[0]["title"], "Binary arithmetic")
		self.assertIn("ILIKE", fake_connection.query)
		self.assertNotIn("MATCH", fake_connection.query)

	def test_chat_creates_only_a_mastercontrol_proposal(self):
		prediction = {"intent": "CREATE_DEADLINE", "confidence": 0.99, "confidence_band": "high", "entities": {"course": "HDL", "date": "tomorrow", "time": "18:00", "title": "lab report"}}
		with patch("app.utils.assistant.predict", return_value=prediction):
			response = self.client.post("/api/assistant/chat", json={"message": "Please add a deadline for HDL tomorrow at 6 PM titled lab report."})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.get_json()["tool"], "create_deadline")
		self.assertEqual(list_tasks(self.database_path), [])

	def test_mastercontrol_requires_pin_confirmation_and_is_single_use(self):
		arguments = {"title": "Lab report", "course": "HDL", "description": "Lab report", "datetime": "tomorrow 18:00"}
		missing_pin = self.client.post("/api/assistant/action/prepare", json={"tool": "create_deadline", "arguments": arguments})
		self.assertEqual(missing_pin.status_code, 403)
		prepared = self.client.post("/api/assistant/action/prepare", json={"pin": "123456", "tool": "create_deadline", "arguments": arguments})
		self.assertEqual(prepared.status_code, 202)
		token = prepared.get_json()["confirmation_token"]
		without_confirmation = self.client.post("/api/assistant/action/execute", json={"confirmation_token": token})
		self.assertEqual(without_confirmation.status_code, 400)
		executed = self.client.post("/api/assistant/action/execute", json={"confirmation_token": token, "confirm": True})
		self.assertEqual(executed.status_code, 200)
		replayed = self.client.post("/api/assistant/action/execute", json={"confirmation_token": token, "confirm": True})
		self.assertEqual(replayed.status_code, 403)
		self.assertEqual(len(list_tasks(self.database_path)), 1)

	def test_prediction_validation_rejects_invalid_data(self):
		with self.assertRaises(EarllmInvalidResponse):
			validate_prediction({"intent": "DELETE_DEADLINE", "confidence": 2, "confidence_band": "high", "entities": {"deadline_id": 7}})
		with self.assertRaises(EarllmInvalidResponse):
			validate_prediction({"intent": "DELETE_DEADLINE", "confidence": 0.9, "confidence_band": "high", "entities": {"deadline_id": 0}})


if __name__ == "__main__":
	unittest.main()
