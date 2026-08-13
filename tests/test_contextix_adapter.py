import os
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

from core.memory.project_context import ProjectContext
from core.memory.contextix_adapter import ContextixAdapter, ContextState


class TestContextixAdapter(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="dinggo_test_contextix_")
        self.project_context = ProjectContext(working_dir=self.test_dir)
        self.adapter = ContextixAdapter(self.project_context)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_has_context_missing(self):
        self.assertFalse(self.adapter.has_context())
        self.assertEqual(self.adapter.get_relevant_context(), "")
        self.assertEqual(self.adapter.state, ContextState.DIRTY)

    def test_has_context_present_and_relevant_query(self):
        context_dir = os.path.join(self.test_dir, ".context")
        os.makedirs(context_dir, exist_ok=True)
        
        bootstrap_path = os.path.join(context_dir, "bootstrap.md")
        with open(bootstrap_path, "w", encoding="utf-8") as f:
            f.write("# Project Bootstrap Context\nThis project is a CLI IDE.")

        yaml_path = os.path.join(context_dir, "context.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("project:\n  name: TestProj\nconstraints:\n  - Must use Python 3.10+\ndecisions:\n  - what: Use SQLite\n    why: Zero config\n")

        adapter = ContextixAdapter(self.project_context)
        self.assertTrue(adapter.has_context())
        self.assertEqual(adapter.state, ContextState.CLEAN)

        relevant = adapter.get_relevant_context(target_scope=["database.py"], summary="Refactor database")
        self.assertIn("Must use Python 3.10+", relevant)
        self.assertIn("Use SQLite", relevant)

    def test_state_machine_dirty_marking(self):
        self.adapter.state = ContextState.CLEAN
        self.adapter.mark_dirty()
        self.assertEqual(self.adapter.state, ContextState.DIRTY)

    def test_agent_state_decoupling(self):
        agent_ctx = self.adapter.get_agent_state_context(current_task="Fix bug", current_phase="Execution")
        self.assertIn("Dinggo Active Agent State", agent_ctx)
        self.assertIn("Fix bug", agent_ctx)
        self.assertIn("Execution", agent_ctx)

    @patch("subprocess.run")
    def test_run_generate_mock(self, mock_subprocess):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "Generated .context/ successfully"
        mock_res.stderr = ""
        mock_subprocess.return_value = mock_res

        self.adapter.is_available = MagicMock(return_value=True)
        res = self.adapter.run_generate()

        self.assertTrue(res["success"])
        self.assertEqual(self.adapter.state, ContextState.CLEAN)

    def test_get_status(self):
        status = self.adapter.get_status()
        self.assertIn("state", status)
        self.assertIn("available", status)
        self.assertIn("has_context", status)
        self.assertIn("decisions_count", status)


if __name__ == "__main__":
    unittest.main()
