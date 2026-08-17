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

from core.reviewer.adapters import get_reviewer_adapter, get_available_reviewers
from core.reviewer.models import ReviewReport, ReviewSeverity, ReviewMode
from core.reviewer.review_engine import ReviewEngine
from core.spec.parser import SpecParser
from core.state.state_manager import StateManager


class ReviewDashboard:
    """Renders scoped Review Packages and 4-quadrant code audit reports."""

    def __init__(
        self,
        root_dir: str = ".",
        console: Optional[Console] = None,
        state_manager: Optional[StateManager] = None,
        adapter_name: Optional[str] = None,
        mode: str = "targeted"
    ):
        self.root_dir = root_dir
        self.console = console or Console()
        self.state_mgr = state_manager or StateManager(self.root_dir)
        adapter = get_reviewer_adapter(adapter_name, root_dir=self.root_dir)
        self.engine = ReviewEngine(self.root_dir, state_manager=self.state_mgr, adapter=adapter, mode=mode)

    def display_and_run(self, interactive: bool = True) -> Optional[ReviewReport]:
        """Executes independent audit and displays results in formatted TUI."""
        from cli.menu_selector import select_menu_option

        self.console.print("\n[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]")
        self.console.print("[bold bright_magenta]  🛡️  INDEPENDENT CODE AUDITOR & QUALITY REVIEW[/bold bright_magenta]")
        self.console.print("[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]\n")

        available = get_available_reviewers(self.root_dir)

        if interactive and len(available) > 1:
            options = []
            for idx, r in enumerate(available, start=1):
                category = "External CLI" if r["id"] in ("codex", "agy", "claude") else ("Local LLM" if r["id"] == "ollama" else "Heuristic")
                options.append((f"{idx}. {r['name']}", f"Run {category} audit", r["id"]))
            options.append((f"{len(available) + 1}. Cancel", "Return to main menu", "cancel"))

            selected = select_menu_option("SELECT INDEPENDENT AUDITOR", options)
            if not selected or selected == "cancel":
                return None

            self.engine.adapter = get_reviewer_adapter(selected, root_dir=self.root_dir)

        auditor_name = getattr(self.engine.adapter, "name", "Independent Auditor")
        mode_label = "Targeted Review (Per-Requirement Packages)" if self.engine.mode == "targeted" else "Full Repository Audit"
        
        self.console.print(f"[bold white]Active Auditor:[/bold white] [bold yellow]{auditor_name}[/bold yellow]")
        self.console.print(f"[bold white]Audit Scope:[/bold white]    [bold cyan]{mode_label}[/bold cyan]\n")

        spec = SpecParser(self.root_dir).parse()
        self.console.print("[dim]Evaluating evidence across Requirements, Quality, Security, and Architecture...[/dim]")

        res = self.engine.run_review_loop(spec=spec)
        report: ReviewReport = res["report"]

        # Report Header Table
        hdr_table = Table(box=None, show_header=False, padding=(0, 2))
        hdr_table.add_column("Field", style="bold cyan", width=20)
        hdr_table.add_column("Value", style="bold white")

        score_color = "green" if report.score >= 85 else ("yellow" if report.score >= 70 else "red")
        hdr_table.add_row("Auditor:", report.auditor)
        hdr_table.add_row("Review Mode:", report.mode.value.upper() if hasattr(report.mode, "value") else str(report.mode).upper())
        hdr_table.add_row("Packages Reviewed:", str(report.packages_reviewed))
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
            f_table = Table(title="Detected Audit Findings & Concrete Evidence", border_style="dim", padding=(0, 1))
            f_table.add_column("ID", style="bold yellow", width=10)
            f_table.add_column("Req", style="cyan", width=10)
            f_table.add_column("Category", style="magenta", width=13)
            f_table.add_column("Severity", style="bold", width=10)
            f_table.add_column("Title / Evidence", style="white")

            for f in report.findings[:15]:
                sev_color = "red" if f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) else "yellow"
                req_lbl = f.requirement_id or "-"
                title_ev = f"[bold]{f.title}[/bold]"
                if f.evidence:
                    title_ev += f"\n[dim]Evidence: {f.evidence}[/dim]"
                if f.file_path:
                    loc = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
                    title_ev += f" [dim]({loc})[/dim]"

                f_table.add_row(
                    f.id,
                    req_lbl,
                    f.category.value,
                    f"[{sev_color}]{f.severity.value.upper()}[/{sev_color}]",
                    title_ev
                )

            self.console.print(f_table)

        return report
