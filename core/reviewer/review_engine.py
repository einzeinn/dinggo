"""Review Engine & Automated Review-Repair Loop with Scoped Review Packages for Dinggo."""
from typing import Optional, Dict, Any, Callable, List
from core.reviewer.models import (
    ReviewReport,
    ReviewFinding,
    ReviewSeverity,
    ReviewPackage,
    ReviewLevel,
    ReviewMode,
    ContextRequest,
)
from core.reviewer.adapters import BaseReviewerAdapter, MockReviewerAdapter, get_reviewer_adapter
from core.reviewer.package_builder import ReviewPackageBuilder
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class ReviewEngine:
    """
    Coordinates independent code audits using scoped Review Packages and investigative follow-ups.
    Supports Targeted Review (per-requirement evidence) and Full Repository Audits.
    """

    def __init__(
        self,
        root_dir: str = ".",
        state_manager: Optional[StateManager] = None,
        adapter: Optional[BaseReviewerAdapter] = None,
        max_cycles: int = 3,
        mode: str = "targeted",
        level: ReviewLevel = ReviewLevel.LEVEL_1_REQUIREMENT
    ):
        self.root_dir = root_dir
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.adapter = adapter or get_reviewer_adapter(root_dir=self.root_dir)
        self.max_cycles = max_cycles
        self.mode = mode.lower().strip() if mode else "targeted"
        self.level = level
        self.package_builder = ReviewPackageBuilder(self.root_dir)

    def execute_audit(
        self,
        spec: Optional[ProductSpec] = None,
        progress_callback: Optional[Callable[[int, int, str, str, Optional[ReviewReport]], None]] = None
    ) -> ReviewReport:
        """
        Executes a single audit pass across scoped Review Packages with interactive context retrieval.
        """
        if self.mode == "targeted" and spec and spec.requirements:
            packages = self.package_builder.build_targeted_packages(
                spec=spec,
                task_graph=self.state_mgr.state.active_plan,
                state=self.state_mgr.state,
                level=self.level
            )
            return self._audit_packages(packages, spec=spec, progress_callback=progress_callback)
        else:
            full_pkg = self.package_builder.build_full_package(spec=spec)
            if progress_callback:
                progress_callback(1, 1, full_pkg.package_id, full_pkg.requirement_title or "Full Repository", None)
            rep = self._audit_single_package_with_investigation(full_pkg, spec=spec)
            if progress_callback:
                progress_callback(1, 1, full_pkg.package_id, full_pkg.requirement_title or "Full Repository", rep)
            return rep

    def run_review_loop(
        self,
        spec: Optional[ProductSpec] = None,
        custom_fix_func: Optional[Callable[[ReviewReport, int], bool]] = None,
        progress_callback: Optional[Callable[[int, int, str, str, Optional[ReviewReport]], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes independent review and automatic repair cycles if critical/high findings exist.
        """
        self.state_mgr.transition_to(
            PipelinePhase.REVIEWING,
            PipelineStatus.IN_PROGRESS,
            f"Running independent review ({self.mode.upper()} mode)",
            can_resume=True
        )
        cycle = 1

        while cycle <= self.max_cycles:
            self.state_mgr.state.session.review_cycle = cycle
            report = self.execute_audit(spec=spec, progress_callback=progress_callback)

            if report.verdict == "approved":
                self.state_mgr.transition_to(
                    PipelinePhase.COMPLETED,
                    PipelineStatus.SUCCESS,
                    f"Independent audit passed with score {report.score:.1f}/100",
                    can_resume=True
                )
                return {
                    "success": True,
                    "cycles": cycle,
                    "report": report
                }

            # Revisions required
            self.state_mgr.transition_to(
                PipelinePhase.REVIEW_REPAIRING,
                PipelineStatus.IN_PROGRESS,
                f"Review-repair cycle {cycle}/{self.max_cycles} (Score: {report.score:.1f})",
                can_resume=True
            )

            if custom_fix_func:
                custom_fix_func(report, cycle)
            else:
                self._default_remedy(report)

            cycle += 1

        # Final audit pass after max cycles reached
        final_report = self.execute_audit(spec=spec, progress_callback=progress_callback)
        success = final_report.verdict == "approved"
        if success:
            self.state_mgr.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, "Independent audit approved after repair cycles")
        else:
            self.state_mgr.transition_to(
                PipelinePhase.FAILED,
                PipelineStatus.PAUSED,
                f"Independent audit requires manual review (Score: {final_report.score:.1f})",
                can_resume=True
            )

        return {
            "success": success,
            "cycles": self.max_cycles,
            "report": final_report
        }

    def _audit_packages(
        self,
        packages: List[ReviewPackage],
        spec: Optional[ProductSpec] = None,
        progress_callback: Optional[Callable[[int, int, str, str, Optional[ReviewReport]], None]] = None
    ) -> ReviewReport:
        """
        Audits a list of targeted ReviewPackages sequentially, aggregating findings and score.
        """
        all_findings: List[ReviewFinding] = []
        auditor_name = getattr(self.adapter, "name", "Independent Auditor")
        context_reqs: List[ContextRequest] = []
        pkg_reports: List[ReviewReport] = []

        total_pkgs = len(packages)
        for idx, pkg in enumerate(packages, start=1):
            pkg_title = pkg.requirement_title or pkg.requirement_id or "Module"
            if progress_callback:
                progress_callback(idx, total_pkgs, pkg.package_id, pkg_title, None)

            pkg_report = self._audit_single_package_with_investigation(pkg, spec=spec)
            pkg_reports.append(pkg_report)
            auditor_name = pkg_report.auditor
            all_findings.extend(pkg_report.findings)
            context_reqs.extend(pkg_report.context_requests)

            if progress_callback:
                progress_callback(idx, total_pkgs, pkg.package_id, pkg_title, pkg_report)

        # Calculate overall aggregated score and verdict
        if pkg_reports:
            score = sum(r.score for r in pkg_reports) / len(pkg_reports)
        else:
            score = 100.0

        for f in all_findings:
            if f.severity == ReviewSeverity.CRITICAL:
                score = min(score, 60.0)
            elif f.severity == ReviewSeverity.HIGH:
                score = min(score, 75.0)

        score = max(0.0, min(100.0, score))

        if score >= 90.0 and not any(f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) for f in all_findings):
            verdict = "approved"
        elif score >= 70.0:
            verdict = "revisions_required"
        else:
            verdict = "rejected"

        summary = f"Targeted audit complete across {len(packages)} packages. Score: {score:.1f}/100. Verdict: {verdict.upper()} ({len(all_findings)} findings)."

        return ReviewReport(
            auditor=auditor_name,
            score=score,
            verdict=verdict,
            findings=all_findings,
            summary=summary,
            mode=ReviewMode.TARGETED,
            packages_reviewed=len(packages),
            context_requests=context_reqs
        )

    def _audit_single_package_with_investigation(
        self,
        package: ReviewPackage,
        spec: Optional[ProductSpec] = None,
        max_investigation_rounds: int = 2
    ) -> ReviewReport:
        """
        Runs investigative audit on a single package. If reviewer requests context, retrieves files and re-audits.
        """
        round_num = 1
        current_pkg = package
        final_report: Optional[ReviewReport] = None

        while round_num <= max_investigation_rounds:
            report = self.adapter.audit(self.root_dir, spec=spec, package=current_pkg)
            final_report = report

            # If reviewer requested additional files and rounds remain, retrieve context
            if report.context_requests and round_num < max_investigation_rounds:
                for cr in report.context_requests:
                    current_pkg = self.package_builder.retrieve_context(current_pkg, cr)
                round_num += 1
            else:
                break

        return final_report or ReviewReport(auditor=getattr(self.adapter, "name", "Auditor"), score=100.0, verdict="approved")

    def _default_remedy(self, report: ReviewReport) -> None:
        """Default heuristic remedy handler."""
        pass
