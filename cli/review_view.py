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

        if interactive:
            from core.reviewer.models import ReviewLevel
            scope_options = [
                (
                    "1. Level 1: Requirement Review (Targeted)",
                    "Verify acceptance criteria & detect fake/mock returns per requirement",
                    ("targeted", ReviewLevel.LEVEL_1_REQUIREMENT)
                ),
                (
                    "2. Level 2: Code Quality Review (Targeted)",
                    "Audit code correctness, error handling, typing & maintainability",
                    ("targeted", ReviewLevel.LEVEL_2_CODE)
                ),
                (
                    "3. Level 3: Security & Vulnerability Review (Targeted)",
                    "Audit auth bypass, credentials, injection, secrets & CORS",
                    ("targeted", ReviewLevel.LEVEL_3_SECURITY)
                ),
                (
                    "4. Level 4: Full Repository Audit",
                    "Comprehensive review across entire codebase, architecture & configs",
                    ("full", ReviewLevel.LEVEL_4_FULL_AUDIT)
                ),
                ("5. Cancel", "Return to main menu", "cancel")
            ]

            selected_scope = select_menu_option("SELECT AUDIT SCOPE / LEVEL", scope_options)
            if not selected_scope or selected_scope == "cancel":
                return None

            selected_mode, selected_level = selected_scope
            self.engine.mode = selected_mode
            self.engine.level = selected_level

        auditor_name = getattr(self.engine.adapter, "name", "Independent Auditor")
        scope_name = f"Level {self.engine.level.value.replace('_', ' ').title()}" if hasattr(self.engine.level, "value") else str(self.engine.level)
        mode_label = f"Targeted ({scope_name})" if self.engine.mode == "targeted" else f"Full ({scope_name})"
        
        self.console.print(f"[bold white]Active Auditor:[/bold white] [bold yellow]{auditor_name}[/bold yellow]")
        self.console.print(f"[bold white]Audit Scope:[/bold white]    [bold cyan]{mode_label}[/bold cyan]\n")

        spec = SpecParser(self.root_dir).parse()
        self.console.print("[dim]Evaluating evidence across Requirements, Quality, Security, and Architecture...[/dim]\n")

        def on_progress(idx: int, total: int, pkg_id: str, title: str, rep: Optional[ReviewReport]):
            if rep is None:
                self.console.print(f"  [cyan]➜[/cyan] [bold white][{idx}/{total}][/bold white] Auditing [bold yellow]{title}[/bold yellow]...")
            else:
                score_col = "green" if rep.score >= 85 else ("yellow" if rep.score >= 70 else "red")
                self.console.print(f"    [{score_col}]✓[/{score_col}] Score: [{score_col}]{rep.score:.1f}/100[/{score_col}] · Verdict: {rep.verdict.upper()} ({len(rep.findings)} findings)\n")

        res = self.engine.run_review_loop(spec=spec, progress_callback=on_progress)
        report: ReviewReport = res["report"]

        # 1. Executive Summary & Verdict Card
        score_color = "green" if report.score >= 85 else ("yellow" if report.score >= 70 else "red")
        verdict_badge = f"[{score_color} bold]{report.verdict.upper()}[/{score_color} bold]"
        
        # Meter bar
        bar_len = 20
        filled_len = int((report.score / 100.0) * bar_len)
        meter_str = f"[{score_color}]{'█' * filled_len}{'░' * (bar_len - filled_len)}[/{score_color}]"

        summary_content = ""
        if report.executive_summary:
            summary_content += f"[bold white]{report.executive_summary}[/bold white]\n\n"
        elif report.summary:
            summary_content += f"[bold white]{report.summary}[/bold white]\n\n"

        summary_content += f"[dim]•[/dim] [bold cyan]Auditor Engine:[/bold cyan]    {report.auditor}\n"
        summary_content += f"[dim]•[/dim] [bold cyan]Audit Scope:[/bold cyan]       {mode_label}\n"
        summary_content += f"[dim]•[/dim] [bold cyan]Quality Score:[/bold cyan]     [{score_color} bold]{report.score:.1f} / 100[/] {meter_str}\n"
        summary_content += f"[dim]•[/dim] [bold cyan]Audit Verdict:[/bold cyan]     {verdict_badge}\n"
        summary_content += f"[dim]•[/dim] [bold cyan]Packages Checked:[/bold cyan]  {report.packages_reviewed} module package(s)\n"
        summary_content += f"[dim]•[/dim] [bold cyan]Total Findings:[/bold cyan]    {len(report.findings)} defect(s) detected"

        self.console.print(Panel(
            summary_content,
            title="[bold bright_magenta]🛡️  Independent Audit Executive Report[/bold bright_magenta]",
            border_style="bright_magenta",
            padding=(1, 2)
        ))

        # 2. 4-Quadrant Code Audit Scorecard
        quadrant_table = Table(box=None, show_header=True, padding=(0, 1), header_style="bold bright_cyan")
        quadrant_table.add_column("Quadrant Dimension", style="bold white", width=26)
        quadrant_table.add_column("Score", width=12)
        quadrant_table.add_column("Auditor Assessment & Traceability Details", style="white")

        q_names = [
            ("requirements", "📋 Requirements Traceability", "requirements"),
            ("code_quality", "💎 Code Quality & Typing", "code_quality"),
            ("security", "🔒 Security & Hardening", "security"),
            ("architecture", "🏛️ Architecture & Layering", "architecture")
        ]

        for q_key, q_label, cat_name in q_names:
            q_score = report.quadrant_scores.get(q_key, report.score)
            q_col = "green" if q_score >= 85 else ("yellow" if q_score >= 70 else "red")
            q_note = report.quadrant_notes.get(q_key, "Evaluation complete.")
            quadrant_table.add_row(
                q_label,
                f"[{q_col} bold]{q_score:.1f} / 100[/]",
                q_note
            )

        self.console.print(Panel(
            quadrant_table,
            title="[bold cyan]📊 4-Quadrant Quality & Security Scorecard[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        ))

        # 3. Audited Target Artifacts & Files
        if report.verified_files:
            file_list_str = "\n".join([f"  [green]✓[/green] [dim]{f}[/dim]" for f in report.verified_files[:10]])
            if len(report.verified_files) > 10:
                file_list_str += f"\n  [dim]... (+{len(report.verified_files) - 10} more files verified)[/dim]"
            self.console.print(Panel(
                file_list_str,
                title="[bold green]📁 Verified Source Code & Artifacts[/bold green]",
                border_style="dim green",
                padding=(1, 2)
            ))

        # 4. Actionable Recommendations
        if report.recommendations:
            rec_list_str = "\n".join([f"  [yellow]{idx}.[/yellow] {rec}" for idx, rec in enumerate(report.recommendations[:5], start=1)])
            self.console.print(Panel(
                rec_list_str,
                title="[bold yellow]💡 Auditor Recommendations & Next Steps[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))

        # 5. Findings Detail Table (if defects detected)
        if report.findings:
            f_table = Table(title="Detected Audit Findings & Concrete Evidence", border_style="dim red", padding=(0, 1))
            f_table.add_column("ID", style="bold yellow", width=10)
            f_table.add_column("Req", style="cyan", width=10)
            f_table.add_column("Category", style="magenta", width=14)
            f_table.add_column("Severity", style="bold", width=10)
            f_table.add_column("Issue & Evidence", style="white")

            for f in report.findings[:15]:
                sev_color = "red" if f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) else "yellow"
                req_lbl = f.requirement_id or "-"
                title_ev = f"[bold]{f.title}[/bold]"
                if f.file_path:
                    loc = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
                    title_ev += f" [dim]({loc})[/dim]"
                if f.evidence:
                    title_ev += f"\n[dim red]Evidence: {f.evidence}[/dim red]"
                if f.recommendation:
                    title_ev += f"\n[dim green]Fix: {f.recommendation}[/dim green]"

                f_table.add_row(
                    f.id,
                    req_lbl,
                    f.category.value,
                    f"[{sev_color}]{f.severity.value.upper()}[/{sev_color}]",
                    title_ev
                )

            self.console.print(f_table)

        return report
