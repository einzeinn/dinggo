import unittest
from unittest.mock import MagicMock, patch
from core.intent_parser import IntentParser
from core.planner import Planner
from core.executor import Executor
import os
import json

class TestPipelineArchitecture(unittest.TestCase):
    def setUp(self):
        # Mock Ollama Client
        self.mock_client = MagicMock()
        self.intent_parser = IntentParser(ollama_client=self.mock_client)
        self.planner = Planner(ollama_client=self.mock_client)
        self.executor = Executor(ollama_client=self.mock_client)

    def test_intent_user_language_extraction(self):
        # Simulate LLM returning Indonesian request
        self.mock_client.generate.return_value = {
            "success": True,
            "response": '{"category": "TASK", "is_task": true, "user_language": "id", "summary": "check project", "task_type": "general_task", "target_scope": [], "constraints": [], "direct_response": null}'
        }
        res = self.intent_parser.parse("apa yang kamu ketahui tentang project ini")
        self.assertTrue(res["success"])
        self.assertEqual(res["intent"]["user_language"], "id")

    def test_planner_rejects_indonesian(self):
        # The first attempt returns Indonesian
        # The second attempt returns valid English
        self.mock_client.generate.side_effect = [
            {
                "success": True,
                "response": '{"intent_summary": "test", "steps": [{"step_number": 1, "description": "Langkah pertama untuk membaca file", "action_type": "read_file", "target_path": "README.md"}]}'
            },
            {
                "success": True,
                "response": '{"intent_summary": "test", "steps": [{"step_number": 1, "description": "First step to read file", "action_type": "read_file", "target_path": "README.md"}]}'
            }
        ]

        intent_data = {"user_language": "id", "summary": "test"}
        res = self.planner.create_plan(intent_data)
        
        self.assertTrue(res["success"])
        # Should have taken 2 attempts due to the Indonesian validation check in Planner
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(res["plan"]["steps"][0]["description"], "First step to read file")

    def test_executor_strict_read_file_path(self):
        # Target path is missing/empty, it should fail, NOT silently list_dir
        step = {
            "step_number": 1,
            "description": "Read project info",
            "action_type": "read_file",
            "target_path": "-"
        }
        res = self.executor.execute_step(step, "test_workspace")
        self.assertFalse(res["success"])
        self.assertIn("not found or empty", res["error"])

    def test_executor_general_response_warning(self):
        # General response should output a warning about NO execution evidence
        step = {
            "step_number": 1,
            "description": "Synthesize data",
            "action_type": "general_response"
        }
        res = self.executor.execute_step(step, "test_workspace")
        self.assertTrue(res["success"])
        self.assertIn("[WARNING: This is a general response step", res["output"])

if __name__ == "__main__":
    unittest.main()
