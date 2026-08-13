import os
import tempfile
import shutil
import unittest
from unittest.mock import MagicMock, patch

from core.memory.project_context import ProjectContext
from core.memory.contextix_adapter import ContextixAdapter


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
        self.assertEqual(self.adapter.get_formatted_context(), "")

    def test_has_context_present(self):
        context_dir = os.path.join(self.test_dir, ".context")
        os.makedirs(context_dir, exist_ok=True)
        
        bootstrap_path = os.path.join(context_dir, "bootstrap.md")
        with open(bootstrap_path, "w", encoding="utf-8") as f:
            f.write("# Project Bootstrap Context\nThis project is a CLI IDE.")

        yaml_path = os.path.join(context_dir, "context.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write("project:\n  name: TestProj\nconstraints:\n  - Must use Python 3.10+\n")

        self.assertTrue(self.adapter.has_context())
        formatted = self.adapter.get_formatted_context()
        self.assertIn("Project Bootstrap Context", formatted)
        self.assertIn("Must use Python 3.10+", formatted)

    def test_in_memory_caching(self):
        context_dir = os.path.join(self.test_dir, ".context")
        os.makedirs(context_dir, exist_ok=True)
        bootstrap_path = os.path.join(context_dir, "bootstrap.md")
        with open(bootstrap_path, "w", encoding="utf-8") as f:
            f.write("Initial Context Content")

        # First read populates cache
        res1 = self.adapter.get_formatted_context()
        self.assertIn("Initial Context Content", res1)
        self.assertIsNotNone(self.adapter._cached_formatted_str)

        # Second read uses cache
        res2 = self.adapter.get_formatted_context()
        self.assertEqual(res1, res2)

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
        self.assertEqual(mock_subprocess.call_count, 1)

    def test_get_status(self):
        status = self.adapter.get_status()
        self.assertIn("available", status)
        self.assertIn("has_context", status)
        self.assertIn("decisions_count", status)


if __name__ == "__main__":
    unittest.main()
