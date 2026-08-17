"""Closed-Loop Automated Self-Repair Engine for Dinggo Product Factory."""
import time
from typing import Dict, Any, Optional, Callable
from core.testing.test_runner import TestRunner, TestRunSummary
from core.repair.error_analyzer import ErrorAnalyzer
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class RepairEngine:
    """Orchestrates test execution, failure diagnosis, and iterative code patching."""

    def __init__(
        self,
        root_dir: str = ".",
        state_manager: Optional[StateManager] = None,
        max_attempts: int = 5,
        ollama_client: Optional[Any] = None
    ):
        self.root_dir = root_dir
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.max_attempts = max_attempts
        self.client = ollama_client
        self.analyzer = ErrorAnalyzer()
        self.test_runner = TestRunner(self.root_dir)

    def run_repair_loop(
        self,
        custom_patch_func: Optional[Callable[[Dict[str, Any], int], bool]] = None,
        on_cycle_start: Optional[Callable[[int, int, Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes automated testing with closed-loop repair if test failures occur.
        Returns repair loop result summary.
        """
        self.state_mgr.transition_to(PipelinePhase.TESTING, PipelineStatus.IN_PROGRESS, "Running automated test suite", can_resume=True)
        attempt = 1

        while attempt <= self.max_attempts:
            # 1. Run Tests
            test_summary: TestRunSummary = self.test_runner.run_all()
            self.state_mgr.record_test_result(test_summary.total_tests, test_summary.passed_tests)

            if test_summary.success:
                self.state_mgr.transition_to(PipelinePhase.VALIDATING, PipelineStatus.IN_PROGRESS, "Tests passed! Ready for specification validation", can_resume=True)
                return {
                    "success": True,
                    "attempts": attempt,
                    "test_summary": test_summary.model_dump()
                }

            # 2. Diagnose Failures
            self.state_mgr.state.session.repair_cycle = attempt
            self.state_mgr.transition_to(PipelinePhase.REPAIRING, PipelineStatus.IN_PROGRESS, f"Self-repair cycle {attempt}/{self.max_attempts}", can_resume=True)

            primary_failure = test_summary.failures[0]
            diagnosis = self.analyzer.analyze_failure(primary_failure)

            if on_cycle_start:
                on_cycle_start(attempt, self.max_attempts, diagnosis)

            # 3. Apply Patch Strategy
            patched = False
            if custom_patch_func:
                patched = custom_patch_func(diagnosis, attempt)
            else:
                patched = self._default_patch_strategy(diagnosis)

            if not patched:
                # If cannot formulate patch, increment and retry
                pass

            attempt += 1

        # Max attempts exceeded
        self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.PAUSED, f"Repair failed after {self.max_attempts} attempts. Human intervention required.", can_resume=True)
        return {
            "success": False,
            "attempts": self.max_attempts,
            "error": f"Automated repair cycle exhausted ({self.max_attempts}/{self.max_attempts}). Remaining failures present."
        }

    def _default_patch_strategy(self, diagnosis: Dict[str, Any]) -> bool:
        """Default heuristic patcher for syntax/file errors."""
        # Simple no-op fallback
        return True
