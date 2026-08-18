import os
import shutil
import tempfile
import unittest
from core.sandbox.policy import SandboxPolicy
from core.sandbox.runner import SandboxedRunner


class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.policy = SandboxPolicy(allowed_root=self.temp_dir, max_timeout_seconds=5.0)
        self.runner = SandboxedRunner(root_dir=self.temp_dir, policy=self.policy)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_path_boundary_containment(self):
        # Inside workspace
        inside_path = os.path.join(self.temp_dir, "src", "main.py")
        self.assertTrue(self.runner.is_safe_path(inside_path))
        self.assertTrue(self.runner.is_safe_path("relative/path.py"))

        # Parent directory traversal
        outside_path = os.path.join(self.temp_dir, "..", "..", "system32")
        self.assertFalse(self.runner.is_safe_path(outside_path))

        # Absolute system paths
        self.assertFalse(self.runner.is_safe_path("C:\\Windows\\System32"))

    def test_environment_sanitization(self):
        # Inject mock sensitive keys into os.environ
        os.environ["MOCK_OPENAI_API_KEY"] = "sk-secret-12345"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "aws-secret-xyz"
        os.environ["SAFE_APP_ENV"] = "testing"

        try:
            sanitized = self.runner.sanitize_env()
            # Restricted keys must NOT be present
            self.assertNotIn("MOCK_OPENAI_API_KEY", sanitized)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", sanitized)
            # Safe keys must remain
            self.assertEqual(sanitized.get("SAFE_APP_ENV"), "testing")
            # Isolation flags present
            self.assertEqual(sanitized.get("PYTHONDONTWRITEBYTECODE"), "1")
            self.assertIn("127.0.0.1", sanitized.get("HTTP_PROXY", ""))
        finally:
            os.environ.pop("MOCK_OPENAI_API_KEY", None)
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            os.environ.pop("SAFE_APP_ENV", None)

    def test_dangerous_command_detection(self):
        dangerous_cmds = [
            "rm -rf /",
            "rm -rf /etc",
            "rmdir /s /q C:\\",
            "format C:",
            ":(){ :|:& };:",
        ]
        for cmd in dangerous_cmds:
            reason = self.runner.check_dangerous_command(cmd)
            self.assertIsNotNone(reason, f"Dangerous command '{cmd}' should have been intercepted!")

        safe_cmd = "python -m unittest discover tests"
        self.assertIsNone(self.runner.check_dangerous_command(safe_cmd))

    def test_dangerous_python_ast_scan(self):
        malicious_code = "import shutil\nshutil.rmtree('/')"
        reason = self.runner.check_dangerous_python_code(malicious_code)
        self.assertIsNotNone(reason)

        safe_code = "def add(a, b):\n    return a + b"
        self.assertIsNone(self.runner.check_dangerous_python_code(safe_code))

    def test_sandboxed_command_execution(self):
        res = self.runner.run_command("echo hello sandbox", cwd=self.temp_dir)
        self.assertTrue(res["success"])
        self.assertIn("hello sandbox", res["stdout"].strip())
        self.assertTrue(res["sandboxed"])


if __name__ == "__main__":
    unittest.main()
