import unittest
from unittest.mock import MagicMock, patch
from core.executor import Executor
from core.planner import normalize_plan_data
import os

class TestRFC003Contract(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.executor = Executor(ollama_client=self.mock_client)
        self.test_dir = os.path.dirname(os.path.abspath(__file__))

    def test_a_missing_target(self):
        """Test A — Missing target: should fail, no fuzzy search."""
        step = {
            "action_type": "read_file",
            "target_path": "-"
        }
        res = self.executor.execute_step(step, project_root=self.test_dir)
        self.assertFalse(res["success"])
        self.assertIn("Target file path was missing", res["error"])

    def test_b_empty_target(self):
        """Test B — Empty target: should fail."""
        step = {
            "action_type": "read_file",
            "target_path": ""
        }
        res = self.executor.execute_step(step, project_root=self.test_dir)
        self.assertFalse(res["success"])
        self.assertIn("Target file path was missing", res["error"])

    def test_c_valid_read(self):
        """Test C — Valid read: should succeed and have output."""
        # We read this exact test file as a valid target
        test_file = os.path.basename(__file__)
        step = {
            "action_type": "read_file",
            "target_path": test_file
        }
        res = self.executor.execute_step(step, project_root=self.test_dir)
        self.assertTrue(res["success"])
        self.assertIn("def test_c_valid_read", res["output"])

    def test_d_missing_file(self):
        """Test D — Missing file: should fail deterministically without fallback."""
        step = {
            "action_type": "read_file",
            "target_path": "does-not-exist-12345.md"
        }
        res = self.executor.execute_step(step, project_root=self.test_dir)
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

    def test_e_general_response(self):
        """Test E — General response: must not generate fake file evidence."""
        step = {
            "action_type": "general_response",
            "description": "I will search the project"
        }
        res = self.executor.execute_step(step, project_root=self.test_dir)
        self.assertFalse(res["success"])
        self.assertTrue(res.get("is_response_only"))
        self.assertIn("NO files were read and NO execution evidence was gathered", res["output"])

    def test_f_planner_validation(self):
        """Test F — Knowledge request planner validation."""
        # Ensure invalid actions raise ValueError instead of silent fallback
        plan_data = {
            "steps": [
                {
                    "action_type": "unknown_action_xyz",
                    "target_path": "README.md"
                }
            ]
        }
        with self.assertRaises(ValueError) as context:
            normalize_plan_data(plan_data)
        self.assertIn("Invalid action_type", str(context.exception))
