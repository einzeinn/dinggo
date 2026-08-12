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

    def test_intent_parser_non_task_classification(self):
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            "success": True,
            "response": '{"is_task": false, "task_type": "chat", "summary": "Salam pembuka", "direct_response": "Halo! Ada yang bisa saya bantu?"}'
        }

        parser = IntentParser(ollama_client=mock_client)
        res = parser.parse("hi")

        self.assertTrue(res["success"])
        self.assertFalse(res["intent"]["is_task"])
        self.assertEqual(res["intent"]["direct_response"], "Halo! Ada yang bisa saya bantu?")

    def test_intent_parser_categories(self):
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            {"success": True, "response": '{"category": "TASK", "is_task": true, "summary": "Tambah fungsi", "task_type": "edit_file"}'},
            {"success": True, "response": '{"category": "CONVERSATION", "is_task": false, "summary": "Salam", "direct_response": "Halo juga!"}'},
            {"success": True, "response": '{"category": "CLARIFICATION", "is_task": false, "summary": "Ambigu", "direct_response": "File mana yang ingin diubah?"}'}
        ]

        parser = IntentParser(ollama_client=mock_client)
        
        r1 = parser.parse("Ubah file utils.py")
        self.assertEqual(r1["intent"]["category"], "TASK")
        self.assertTrue(r1["intent"]["is_task"])

        r2 = parser.parse("Halo bro")
        self.assertEqual(r2["intent"]["category"], "CONVERSATION")
        self.assertFalse(r2["intent"]["is_task"])

        r3 = parser.parse("Perbaiki kodenya dong")
        self.assertEqual(r3["intent"]["category"], "CLARIFICATION")
        self.assertEqual(r3["intent"]["direct_response"], "File mana yang ingin diubah?")

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
