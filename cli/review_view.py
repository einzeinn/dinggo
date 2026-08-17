"""Reviewer Dashboard & Audit Report UI Component for Dinggo Product Factory."""
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.reviewer.models import ReviewReport, ReviewSeverity
from core.reviewer.review_engine import ReviewEngine
from core.spec.parser import SpecParser
from core.state.state_manager import StateManager


class ReviewDashboard:
    """Renders 4-quadrant code audit reports and findings."""

    def __init__(self, root_dir: str = ".", console: Optional[Console] = None, state_manager: Optional[StateManager] = None):
        self.root_dir = root_dir
        self.console = console or Console()
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.engine = ReviewEngine(self.root_dir, state_manager=self.state_mgr)

    def display_and_run(self) -> ReviewReport:
        """Executes independent audit and displays results in formatted TUI."""
        self.console.print("\n[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]")
        self.console.print("[bold bright_magenta]  🛡️  INDEPENDENT CODE AUDITOR & QUALITY REVIEW[/bold bright_magenta]")
        self.console.print("[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]\n")

        spec = SpecParser(self.root_dir).parse()
        self.console.print("[dim]Auditing codebase across Requirements, Quality, Security, and Architecture...[/dim]")

        res = self.engine.run_review_loop(spec=spec)
        report: ReviewReport = res["report"]

        # Report Header Table
        hdr_table = Table(box=None, show_header=False, padding=(0, 2))
        hdr_table.add_column("Field", style="bold cyan", width=18)
        hdr_table.add_column("Value", style="bold white")

        score_color = "green" if report.score >= 85 else ("yellow" if report.score >= 70 else "red")
        hdr_table.add_row("Auditor:", report.auditor)
        hdr_table.add_row("Quality Score:", f"[{score_color}]{report.score:.1f} / 100[/{score_color}]")
        hdr_table.add_row("Verdict:", f"[{score_color}]{report.verdict.upper()}[/{score_color}]")
        hdr_table.add_row("Total Findings:", str(len(report.findings)))

        self.console.print(Panel(
            hdr_table,
            title="[bold bright_magenta]Audit Summary[/bold bright_magenta]",
            border_style="bright_magenta",
            padding=(1, 2)
        ))

        # Findings Detail Table
        if report.findings:
            f_table = Table(title="Detected Audit Findings", border_style="dim", padding=(0, 1))
            f_table.add_column("ID", style="bold yellow", width=10)
            f_table.add_column("Category", style="cyan", width=14)
            f_table.add_column("Severity", style="bold magenta", width=10)
            f_table.add_column("Location", style="dim", width=22)
            f_table.add_column("Description", style="white")

            for f in report.findings[:10]:
                loc = f"{f.file_path}:{f.line_number}" if f.file_path else "Repository"
                sev_color = "red" if f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) else "yellow"
                f_table.add_row(
                    f.id,
                    f.category.value,
                    f"[{sev_color}]{f.severity.value.upper()}[/{sev_color}]",
                    loc,
                    f.title
                )

            self.console.print(f_table)

        return report
