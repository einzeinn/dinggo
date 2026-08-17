"""Review Engine & Automated Review-Repair Loop for Dinggo Product Factory."""
from typing import Optional, Dict, Any, Callable
from core.reviewer.models import ReviewReport, ReviewSeverity
from core.reviewer.adapters import BaseReviewerAdapter, MockReviewerAdapter
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class ReviewEngine:
    """Coordinates independent audits and automated review-repair cycles."""

    def __init__(
        self,
        root_dir: str = ".",
        state_manager: Optional[StateManager] = None,
        adapter: Optional[BaseReviewerAdapter] = None,
        max_cycles: int = 3
    ):
        self.root_dir = root_dir
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.adapter = adapter or MockReviewerAdapter()
        self.max_cycles = max_cycles

    def run_review_loop(
        self,
        spec: Optional[ProductSpec] = None,
        custom_fix_func: Optional[Callable[[ReviewReport, int], bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes audit and automatic repair loop if critical findings exist.
        """
        self.state_mgr.transition_to(PipelinePhase.REVIEWING, PipelineStatus.IN_PROGRESS, "Running independent 4-quadrant code audit", can_resume=True)
        cycle = 1

        while cycle <= self.max_cycles:
            self.state_mgr.state.session.review_cycle = cycle
            report = self.adapter.audit(self.root_dir, spec=spec)

            if report.verdict == "approved":
                self.state_mgr.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, f"Independent audit passed with score {report.score}/100", can_resume=True)
                return {
                    "success": True,
                    "cycles": cycle,
                    "report": report
                }

            # Needs revisions
            self.state_mgr.transition_to(PipelinePhase.REVIEW_REPAIRING, PipelineStatus.IN_PROGRESS, f"Review-repair cycle {cycle}/{self.max_cycles} (Score: {report.score:.1f})", can_resume=True)

            if custom_fix_func:
                custom_fix_func(report, cycle)
            else:
                self._default_remedy(report)

            cycle += 1

        # Max review cycles reached
        final_report = self.adapter.audit(self.root_dir, spec=spec)
        success = final_report.verdict == "approved"
        if success:
            self.state_mgr.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, "Independent audit approved after repair cycles")
        else:
            self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.PAUSED, f"Independent audit requires manual review (Score: {final_report.score:.1f})", can_resume=True)

        return {
            "success": success,
            "cycles": self.max_cycles,
            "report": final_report
        }

    def _default_remedy(self, report: ReviewReport) -> None:
        """Default heuristic auto-remediation for detected findings."""
        pass
