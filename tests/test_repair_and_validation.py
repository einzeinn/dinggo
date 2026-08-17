"""Unit tests for Phase 5: Automated Testing, Repair Engine, and Validation Gate 2."""
import io
import os
import shutil
import tempfile
import unittest
from rich.console import Console

from core.testing.test_runner import TestRunner, TestFailure, TestRunSummary
from core.repair.error_analyzer import ErrorAnalyzer
from core.repair.repair_engine import RepairEngine
from core.validation.requirement_validator import RequirementValidator, ValidationResult
from core.spec.models import ProductSpec, RequirementItem, ArchitectureSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from cli.gates.validation_review import ValidationReviewGate


class TestRepairAndValidation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_error_analyzer(self):
        """Test analyzing stack traces and extracting root cause and line numbers."""
        analyzer = ErrorAnalyzer()
        stack = (
            'Traceback (most recent call last):\n'
            '  File "inventory/service.py", line 42, in create_item\n'
            '    raise ValueError("Invalid SKU format")\n'
            'ValueError: Invalid SKU format'
        )
        fail = TestFailure(
            test_id="TEST-001",
            test_name="test_sku_creation",
            error_message="ValueError: Invalid SKU format",
            stack_trace=stack
        )
        diag = analyzer.analyze_failure(fail)
        self.assertEqual(diag["target_file"], "inventory/service.py")
        self.assertEqual(diag["line_number"], 42)
        self.assertEqual(diag["root_cause"], "ValueError: Invalid SKU format")

    def test_repair_engine_closed_loop(self):
        """Test closed-loop repair engine fixing a failure on attempt 2."""
        engine = RepairEngine(root_dir=self.test_dir, state_manager=self.state_mgr, max_attempts=3)

        # Mock a patcher that fixes the problem after attempt 1
        attempt_counter = [0]
        def mock_patch(diagnosis, attempt):
            attempt_counter[0] += 1
            return True

        # Mock test runner run_all to fail on attempt 1, pass on attempt 2
        call_count = [0]
        def mock_run_all():
            call_count[0] += 1
            if call_count[0] == 1:
                return TestRunSummary(
                    total_tests=5,
                    passed_tests=4,
                    failed_tests=1,
                    failures=[TestFailure(test_id="T1", test_name="test_1", error_message="AssertionError", stack_trace='File "app.py", line 10\nAssertionError')],
                    success=False
                )
            else:
                return TestRunSummary(total_tests=5, passed_tests=5, failed_tests=0, success=True)

        engine.test_runner.run_all = mock_run_all
        res = engine.run_repair_loop(custom_patch_func=mock_patch)

        self.assertTrue(res["success"])
        self.assertEqual(res["attempts"], 2)
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.VALIDATING)

    def test_requirement_validator(self):
        """Test specification traceability validation against ProductSpec."""
        spec = ProductSpec(
            name="Inventory App",
            requirements=[
                RequirementItem(id="AUTH-001", title="Auth", description="login", priority="critical"),
                RequirementItem(id="INV-001", title="Inventory", description="create item", priority="high")
            ],
            architecture=ArchitectureSpec(constraints=["No plaintext secrets"])
        )

        validator = RequirementValidator(root_dir=self.test_dir)
        res = validator.validate(spec, state=self.state_mgr.state)
        self.assertTrue(res.success)
        self.assertEqual(res.satisfied_requirements, 2)
        self.assertEqual(res.total_requirements, 2)

    def test_validation_review_gate(self):
        """Test ValidationReviewGate approval in non-interactive mode."""
        gate = ValidationReviewGate(console=self.console)
        val_res = ValidationResult(
            total_requirements=10,
            satisfied_requirements=10,
            total_acceptance_criteria=5,
            satisfied_acceptance_criteria=5,
            total_architecture_constraints=2,
            satisfied_architecture_constraints=2,
            success=True
        )
        approved, feedback = gate.review_and_confirm(val_res, non_interactive=True)
        self.assertTrue(approved)
        self.assertIsNone(feedback)


if __name__ == "__main__":
    unittest.main()
