import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import create_app
from app.models import list_notes
from app.services.posts.simple_interest import SimpleInterestError, calculate_simple_interest, solve_simple_interest_problem
from app.utils.rich_text import sanitize_rich_text


class SimpleInterestTests(unittest.TestCase):
	def test_ordinary_uses_thirty_day_months(self):
		result = calculate_simple_interest({
			"basis": "ordinary",
			"solve_for": "future_value",
			"start_date": "2026-01-31",
			"end_date": "2026-02-28",
			"principal": 1000,
			"interest_rate": 12,
		})
		self.assertEqual(result["days"], 27)
		self.assertAlmostEqual(result["future_value"], 1009)

	def test_exact_counts_leap_day(self):
		result = calculate_simple_interest({
			"basis": "exact",
			"solve_for": "future_value",
			"start_date": "2024-02-28",
			"end_date": "2024-03-01",
			"principal": 3650,
			"interest_rate": 10,
		})
		self.assertEqual(result["days"], 2)
		self.assertAlmostEqual(result["interest"], 2)

	def test_each_solve_target(self):
		base = {"basis": "ordinary", "start_date": "2026-01-01", "end_date": "2026-02-01", "interest_rate": 12}
		future_value = calculate_simple_interest({**base, "solve_for": "future_value", "principal": 1000})
		principal = calculate_simple_interest({**base, "solve_for": "principal", "future_value": 1010})
		rate = calculate_simple_interest({**base, "solve_for": "interest_rate", "principal": 1000, "future_value": 1010})
		self.assertAlmostEqual(future_value["future_value"], 1010)
		self.assertAlmostEqual(principal["principal"], 1000)
		self.assertAlmostEqual(rate["interest_rate"], 12)

	def test_reversed_dates_are_rejected(self):
		with self.assertRaisesRegex(SimpleInterestError, "end_date"):
			calculate_simple_interest({
				"basis": "exact",
				"solve_for": "future_value",
				"start_date": "2026-02-01",
				"end_date": "2026-01-01",
				"principal": 1000,
				"interest_rate": 12,
			})

	def test_word_problem_returns_step_by_step_solution(self):
		result = solve_simple_interest_problem("Calculate the simple interest on 1000 at 12% for 2 years.")
		self.assertAlmostEqual(result["interest"], 240)
		self.assertAlmostEqual(result["future_value"], 1240)
		self.assertEqual(len(result["steps"]), 4)
		self.assertIn("I = P", result["steps"][1])

	def test_word_problem_requires_all_core_values(self):
		with self.assertRaisesRegex(SimpleInterestError, "principal, annual rate, and time"):
			solve_simple_interest_problem("Explain simple interest step by step")

	def test_word_problem_can_solve_for_rate(self):
		result = solve_simple_interest_problem("Find the annual rate if 1000 becomes 1120 after 2 years with simple interest.")
		self.assertAlmostEqual(result["interest_rate"], 6)
		self.assertIn("Annual interest rate", result["steps"][-1])

	def test_api_is_transient_and_validates_payload(self):
		with tempfile.TemporaryDirectory() as directory:
			database_path = str(Path(directory) / "test.db")
			with patch("app.DATABASE_URL", ""), patch("app.DATABASE_PATH", Path(database_path)):
				app = create_app()
			app.config.update(TESTING=True, DATABASE_PATH=database_path)
			client = app.test_client()
			response = client.post("/api/interactive/simple-interest", json={
				"basis": "ordinary",
				"solve_for": "future_value",
				"start_date": "2026-01-01",
				"end_date": "2026-02-01",
				"principal": 1000,
				"interest_rate": 12,
			})
			self.assertEqual(response.status_code, 200)
			self.assertEqual(response.get_json()["result"]["days"], 30)
			self.assertEqual(list_notes(database_path), [])

			invalid = client.post("/api/interactive/simple-interest", json={"basis": "ordinary"})
			self.assertEqual(invalid.status_code, 400)
			self.assertIn("start_date", invalid.get_json()["error"])

	def test_compound_interest_api_returns_full_solution(self):
		with tempfile.TemporaryDirectory() as directory:
			database_path = str(Path(directory) / "test.db")
			with patch("app.DATABASE_URL", ""), patch("app.DATABASE_PATH", Path(database_path)):
				app = create_app()
			app.config.update(TESTING=True, DATABASE_PATH=database_path)
			client = app.test_client()
			response = client.post("/api/interactive/compound-interest", json={
				"solve_for": "future_value",
				"principal": 1000,
				"interest_rate": 12,
				"n": 2,
			})
			self.assertEqual(response.status_code, 200)
			self.assertIn("steps", response.get_json()["result"])
			self.assertIn("F = P(1 + i)^n", response.get_json()["result"]["formula"])

	def test_formula_paste_markup_is_kept_in_rich_text(self):
		safe = sanitize_rich_text('<span class="math-fraction"><span class="math-num">A</span><span class="math-bar"></span><span class="math-den">B</span></span> <span class="math-sup">n</span>')
		self.assertIn('math-fraction', safe)
		self.assertIn('math-sup', safe)

	def test_all_interactive_lesson_posts_are_registered(self):
		with tempfile.TemporaryDirectory() as directory:
			database_path = str(Path(directory) / "test.db")
			with patch("app.DATABASE_URL", ""), patch("app.DATABASE_PATH", Path(database_path)):
				create_app()
			connection = sqlite3.connect(database_path)
			try:
				source_keys = [row[0] for row in connection.execute("SELECT source_key FROM interactive_sources").fetchall()]
				self.assertIn("simple_interest_lesson", source_keys)
				self.assertIn("compound_interest_lesson", source_keys)
				self.assertIn("discount_lesson", source_keys)
				self.assertIn("equation_of_value_lesson", source_keys)
				self.assertIn("nominal_rate_lesson", source_keys)
				self.assertIn("effective_rate_lesson", source_keys)
				self.assertIn("continuous_compounding_lesson", source_keys)
			finally:
				connection.close()


if __name__ == "__main__":
	unittest.main()
