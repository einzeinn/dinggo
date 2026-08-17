"""Unit tests for Phase 7: Independent Reviewer Engine and Review-Repair Loop."""
import io
import os
import shutil
import tempfile
import unittest
from rich.console import Console

from core.reviewer.models import ReviewReport, ReviewFinding, ReviewSeverity, ReviewCategory
from core.reviewer.adapters import MockReviewerAdapter, BaseReviewerAdapter
from core.reviewer.review_engine import ReviewEngine
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from cli.review_view import ReviewDashboard


class TestReviewerEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mock_reviewer_clean_code(self):
        """Test auditor against clean code produces score 100 and approved verdict."""
        with open(os.path.join(self.test_dir, "clean.py"), "w") as f:
            f.write("def add(a: int, b: int) -> int:\n    return a + b\n")

        adapter = MockReviewerAdapter()
        report = adapter.audit(self.test_dir)
        self.assertEqual(report.verdict, "approved")
        self.assertEqual(report.score, 100.0)
        self.assertEqual(len(report.findings), 0)

    def test_mock_reviewer_security_findings(self):
        """Test auditor detecting hardcoded secret and eval."""
        with open(os.path.join(self.test_dir, "vuln.py"), "w") as f:
            f.write(
                'API_KEY = "sk-123456789"\n'
                'def run_dynamic(cmd):\n'
                '    eval(cmd)\n'
            )

        adapter = MockReviewerAdapter()
        report = adapter.audit(self.test_dir)
        self.assertIn(report.verdict, ("revisions_required", "rejected"))
        self.assertTrue(any(f.category == ReviewCategory.SECURITY for f in report.findings))
        self.assertTrue(report.score < 80.0)

    def test_review_engine_repair_loop(self):
        """Test review engine performing repair loop until approval."""
        vuln_file = os.path.join(self.test_dir, "app.py")
        with open(vuln_file, "w") as f:
            f.write('password = "plaintext_admin_pass"\n')

        def fix_remedy(report: ReviewReport, cycle: int):
            # Patch the vulnerability
            with open(vuln_file, "w") as f:
                f.write('import os\npassword = os.getenv("APP_PASSWORD")\n')
            return True

        engine = ReviewEngine(self.test_dir, state_manager=self.state_mgr, max_cycles=3)
        res = engine.run_review_loop(custom_fix_func=fix_remedy)

        self.assertTrue(res["success"])
        self.assertEqual(res["report"].verdict, "approved")
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.COMPLETED)
        self.assertEqual(self.state_mgr.state.status, PipelineStatus.SUCCESS)

    def test_review_dashboard_render(self):
        """Test review dashboard executes and displays results."""
        dashboard = ReviewDashboard(root_dir=self.test_dir, console=self.console, state_manager=self.state_mgr)
        report = dashboard.display_and_run()
        self.assertIsNotNone(report)
        self.assertEqual(report.verdict, "approved")


if __name__ == "__main__":
    unittest.main()
