import unittest
from unittest.mock import MagicMock
from core.intent_parser import IntentParser, extract_json_payload
from core.planner import Planner, sanitize_thinking_output


class TestIntentAndPlannerRetry(unittest.TestCase):

    def test_extract_json_payload(self):
        raw_markdown = "Berikut JSON-nya:\n```json\n{\"summary\": \"test\", \"task_type\": \"edit_file\"}\n```"
        extracted = extract_json_payload(raw_markdown)
        self.assertEqual(extracted, '{"summary": "test", "task_type": "edit_file"}')

    def test_sanitize_thinking_output(self):
        thinking_text = "<think>\nThinking about task...\n</think>\n{\"intent_summary\": \"Fix bug\", \"steps\": []}"
        sanitized = sanitize_thinking_output(thinking_text)
        self.assertEqual(sanitized, '{"intent_summary": "Fix bug", "steps": []}')

    def test_intent_parser_repair_retry(self):
        mock_client = MagicMock()
        # Attempt 1: Return malformed JSON string
        # Attempt 2: Return valid JSON string
        mock_client.generate.side_effect = [
            {"success": True, "response": '{"summary": "test", invalid_json}'},
            {"success": True, "response": '{"summary": "Tambah helper", "task_type": "create_file", "target_scope": ["utils.py"], "constraints": []}'}
        ]

        parser = IntentParser(ollama_client=mock_client)
        res = parser.parse("Tolong tambahin helper email di utils.py")

        self.assertTrue(res["success"])
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(res["intent"]["summary"], "Tambah helper")
        self.assertEqual(mock_client.generate.call_count, 2)

    def test_planner_repair_retry(self):
        mock_client = MagicMock()
        # Attempt 1: Invalid schema missing required fields
        # Attempt 2: Valid schema
        mock_client.generate.side_effect = [
            {"success": True, "response": '<think>thinking</think>{"wrong_key": "abc"}'},
            {"success": True, "response": '{"intent_summary": "Buat file", "steps": [{"step_number": 1, "description": "Tulis utils.py", "action_type": "write_file", "target_path": "utils.py"}]}'}
        ]

        planner = Planner(ollama_client=mock_client)
        intent = {"task_type": "create_file", "summary": "Buat file"}
        res = planner.create_plan(intent)

        self.assertTrue(res["success"])
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(len(res["plan"]["steps"]), 1)
        self.assertEqual(mock_client.generate.call_count, 2)


if __name__ == "__main__":
    unittest.main()
