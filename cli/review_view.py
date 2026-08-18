"""Reviewer Dashboard, Hub & Audit Report UI Component for Dinggo Product Factory."""
import os
import sys
from typing import Optional, List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.reviewer.adapters import get_reviewer_adapter, get_available_reviewers, ProviderRegistry
from core.reviewer.models import ReviewReport, ReviewSeverity, ReviewCategory, ReviewMode, ReviewFinding
from core.reviewer.review_engine import ReviewEngine
from core.spec.parser import SpecParser
from core.state.state_manager import StateManager
from cli.menu_selector import select_menu_option


class ReviewDashboard:
    """Interactive Reviewer Hub, scoped Review Packages, and 4-quadrant code audit reports."""

    def __init__(
        self,
        root_dir: str = ".",
        console: Optional[Console] = None,
        state_manager: Optional[StateManager] = None,
        adapter_name: Optional[str] = None,
        mode: str = "targeted"
    ):
        self.root_dir = os.path.abspath(root_dir)
        self.console = console or Console()
        self.state_mgr = state_manager or StateManager(self.root_dir)
        adapter = get_reviewer_adapter(adapter_name, root_dir=self.root_dir)
        self.engine = ReviewEngine(self.root_dir, state_manager=self.state_mgr, adapter=adapter, mode=mode)
        self.current_report: Optional[ReviewReport] = self.engine.load_latest_report()

    def display_menu(self) -> None:
        """Main interactive Reviewer Hub navigation loop."""
        while True:
            auditor_name = getattr(self.engine.adapter, "name", "Independent Auditor")
            score_txt = f"{self.current_report.score:.1f}/100 ({self.current_report.verdict.upper()})" if self.current_report else "No audit on record"
            header_extra = f"Reviewer: {auditor_name}  │  Latest Score: {score_txt}"

            options = [
                ("1. Run Audit", "Execute code & environment audit (Level 1-4)", "run"),
                ("2. View Scorecard", "Inspect latest 4-quadrant quality & security report", "view"),
                ("3. Inspect Findings", "Drill-down into code evidence, lines & remediations", "inspect"),
                ("4. Auto-Repair", "Run automated repair loop on open audit findings", "repair"),
                ("5. Export Report", "Generate release audit report (Markdown & JSON)", "export"),
                ("6. Provider Health", "Test AI auditor connectivity & status", "health"),
                ("7. Back", "Return to main factory menu", "back"),
            ]

            choice = select_menu_option("INDEPENDENT REVIEWER HUB", options, header_extra=header_extra)

            if choice in ("back", None, "7"):
                break
            elif choice in ("1", "run"):
                self.display_and_run(interactive=True)
            elif choice in ("2", "view"):
                self.view_latest_report()
            elif choice in ("3", "inspect"):
                self.inspect_findings()
            elif choice in ("4", "repair"):
                self.run_auto_repair()
            elif choice in ("5", "export"):
                self.export_audit_report()
            elif choice in ("6", "health"):
                self.test_providers_health()

    def display_and_run(self, interactive: bool = True) -> Optional[ReviewReport]:
        """Executes independent audit, dynamic environment tests, and displays results in TUI."""
        self.console.print("\n[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]")
        self.console.print("[bold bright_magenta]  🛡️  INDEPENDENT CODE AUDITOR & QUALITY REVIEW[/bold bright_magenta]")
        self.console.print("[bold magenta]══════════════════════════════════════════════════════════════[/bold magenta]\n")

        available = get_available_reviewers(self.root_dir)

        if interactive and len(available) > 1:
            options = []
            for idx, r in enumerate(available, start=1):
                category = "External CLI" if r["id"] in ("codex", "agy", "claude") else ("Local LLM" if r["id"] == "ollama" else "Heuristic")
                options.append((f"{idx}. {r['name']}", f"Run {category} audit", r["id"]))
            options.append((f"{len(available) + 1}. Cancel", "Return to reviewer menu", "cancel"))

            selected = select_menu_option("SELECT INDEPENDENT AUDITOR", options)
            if not selected or selected == "cancel":
                return None

            self.engine.adapter = get_reviewer_adapter(selected, root_dir=self.root_dir)

        if interactive:
            from core.reviewer.models import ReviewLevel
            scope_options = [
                (
                    "1. Level 1: Requirement Review (Targeted)",
                    "Verify acceptance criteria, fake/mock returns & dynamic environment tests",
                    ("targeted", ReviewLevel.LEVEL_1_REQUIREMENT)
                ),
                (
                    "2. Level 2: Code Quality Review (Targeted)",
                    "Audit code correctness, error handling, typing, compilation & runtime",
                    ("targeted", ReviewLevel.LEVEL_2_CODE)
                ),
                (
                    "3. Level 3: Security & Vulnerability Review (Targeted)",
                    "Audit auth bypass, credentials, injection, secrets & CORS",
                    ("targeted", ReviewLevel.LEVEL_3_SECURITY)
                ),
                (
                    "4. Level 4: Full Repository Audit",
                    "Comprehensive review across entire codebase, architecture & environment",
                    ("full", ReviewLevel.LEVEL_4_FULL_AUDIT)
                ),
                ("5. Cancel", "Return to reviewer menu", "cancel")
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

        # Step 1: Live Environment Verification (dynamic execution check)
        self.console.print("[dim]⚡ Step 1/2: Executing dynamic environment tests & syntax compilation checks...[/dim]")
        env_res = self.engine.run_environment_verification()
        if env_res.get("success"):
            self.console.print(f"  [green]✓[/green] Environment tests passed ({env_res.get('passed_tests', 0)}/{env_res.get('total_tests', 0)} tests)\n")
        else:
            self.console.print(f"  [yellow]⚠️[/yellow]  Environment tests failed ({env_res.get('failed_tests', 0)} failure(s) detected). Submitting runtime stack traces to auditor...\n")

        spec = SpecParser(self.root_dir).parse()
        self.console.print("[dim]🛡️  Step 2/2: Evaluating evidence across Requirements, Quality, Security, and Architecture...[/dim]\n")

        def on_progress(idx: int, total: int, pkg_id: str, title: str, rep: Optional[ReviewReport]):
            if rep is None:
                self.console.print(f"  [cyan]➜[/cyan] [bold white][{idx}/{total}][/bold white] Auditing [bold yellow]{title}[/bold yellow]...")
            else:
                score_col = "green" if rep.score >= 85 else ("yellow" if rep.score >= 70 else "red")
                self.console.print(f"    [{score_col}]✓[/{score_col}] Score: [{score_col}]{rep.score:.1f}/100[/{score_col}] · Verdict: {rep.verdict.upper()} ({len(rep.findings)} findings)\n")

        res = self.engine.run_review_loop(spec=spec, progress_callback=on_progress)
        report: ReviewReport = res["report"]
        self.current_report = report

        # Render complete scorecard UI
        self.render_report(report, mode_label=mode_label)

        # Interactive Post-Audit Action Menu
        if interactive:
            self._handle_post_audit_actions(report)

        return report

    def render_report(self, report: ReviewReport, mode_label: str = "Targeted Audit") -> None:
        """Renders executive report card, 4-quadrant table, verified files, recommendations, and findings."""
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

    def _handle_post_audit_actions(self, report: ReviewReport) -> None:
        """Interactive action menu presented directly after audit execution."""
        has_findings = len(report.findings) > 0
        self.console.print("\n[bold white]Post-Audit Actions:[/bold white]")
        choices = ["4"]
        options_txt = ""

        if has_findings:
            options_txt += "[1] Auto-Repair Findings  [2] Inspect Finding Details  "
            choices.extend(["1", "2"])

        options_txt += "[3] Export Report  [4] Return to Hub"
        choices.append("3")

        self.console.print(options_txt)
        choice = Prompt.ask("Choose action", choices=choices, default="4")

        if choice == "1":
            self.run_auto_repair(report)
        elif choice == "2":
            self.inspect_findings(report)
        elif choice == "3":
            self.export_audit_report(report)

    def view_latest_report(self) -> None:
        """Displays latest persisted audit scorecard and findings from disk/memory."""
        report = self.current_report or self.engine.load_latest_report()
        if not report:
            self.console.print("\n[yellow]⚠️  No audit report on record. Run option 1 to execute an audit.[/yellow]\n")
            Prompt.ask("Press Enter to return", default="")
            return

        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  📊 LATEST CODE & ENVIRONMENT AUDIT REPORT[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")
        self.render_report(report, mode_label="Latest Persisted Audit")
        Prompt.ask("\nPress Enter to return", default="")

    def inspect_findings(self, report: Optional[ReviewReport] = None) -> None:
        """Drill-down interactive viewer to inspect specific finding line numbers, evidence & fixes."""
        active_report = report or self.current_report or self.engine.load_latest_report()
        if not active_report or not active_report.findings:
            self.console.print("\n[green]✓ No defects or security vulnerabilities detected to inspect.[/green]\n")
            Prompt.ask("Press Enter to return", default="")
            return

        while True:
            options = []
            for idx, f in enumerate(active_report.findings, start=1):
                sev_tag = f"[{f.severity.value.upper()}]"
                loc = f"({f.file_path})" if f.file_path else ""
                options.append((f"{idx}. {f.id}", f"{sev_tag} {f.title} {loc}", f))
            options.append((f"{len(active_report.findings) + 1}. Return", "Back to reviewer menu", "back"))

            chosen_finding = select_menu_option("INSPECT DEFECT & CODE EVIDENCE", options)
            if not chosen_finding or chosen_finding == "back":
                break

            # Render detailed drill-down card
            f: ReviewFinding = chosen_finding
            detail = f"[bold cyan]Finding ID:[/bold cyan]    {f.id}\n"
            detail += f"[bold cyan]Category:[/bold cyan]      {f.category.value.title()}\n"
            detail += f"[bold cyan]Severity:[/bold cyan]      {f.severity.value.upper()}\n"
            if f.requirement_id:
                detail += f"[bold cyan]Requirement:[/bold cyan]   {f.requirement_id}\n"
            if f.file_path:
                loc_txt = f"{f.file_path}:{f.line_number}" if f.line_number else f.file_path
                detail += f"[bold cyan]Target File:[/bold cyan]   {loc_txt}\n"
            detail += f"\n[bold white]Description:[/bold white]\n{f.description}\n"

            if f.evidence:
                detail += f"\n[bold red]Concrete Evidence & Stack Trace:[/bold red]\n```\n{f.evidence}\n```\n"

            if f.recommendation:
                detail += f"\n[bold green]Remediation Recommendation:[/bold green]\n{f.recommendation}\n"

            # Check if source file exists and display surrounding code preview
            if f.file_path:
                abs_p = os.path.join(self.root_dir, f.file_path)
                if os.path.isfile(abs_p):
                    try:
                        with open(abs_p, "r", encoding="utf-8", errors="ignore") as fp:
                            lines = fp.readlines()
                        target_line = f.line_number or 1
                        start_l = max(1, target_line - 3)
                        end_l = min(len(lines), target_line + 4)
                        code_preview = ""
                        for ln in range(start_l, end_l + 1):
                            prefix = "➜ " if ln == target_line else "  "
                            code_preview += f"{prefix}{ln:4d} | {lines[ln - 1]}"
                        detail += f"\n[bold yellow]Source Code Context ({f.file_path}):[/bold yellow]\n```\n{code_preview}```"
                    except Exception:
                        pass

            self.console.print(Panel(
                detail,
                title=f"[bold red]🔍 Defect Inspector: {f.title}[/bold red]",
                border_style="red",
                padding=(1, 2)
            ))
            Prompt.ask("Press Enter to continue inspecting", default="")

    def run_auto_repair(self, report: Optional[ReviewReport] = None) -> None:
        """Triggers closed-loop repair engine to fix findings and re-verify environment."""
        active_report = report or self.current_report or self.engine.load_latest_report()
        if not active_report or not active_report.findings:
            self.console.print("\n[green]✓ No open findings to repair.[/green]\n")
            Prompt.ask("Press Enter to return", default="")
            return

        self.console.print("\n[bold cyan]🔧 Triggering automated closed-loop self-repair on detected findings...[/bold cyan]")
        success = self.engine._default_remedy(active_report)

        if success:
            self.console.print("[bold green]✓ Self-repair completed! Re-running environment test suite...[/bold green]")
        else:
            self.console.print("[bold yellow]⚠️  Self-repair executed. Running verification pass...[/bold yellow]")

        env_check = self.engine.run_environment_verification()
        if env_check.get("success"):
            self.console.print("[bold green]✓ Environment verification passed![/bold green]")
        else:
            self.console.print(f"[bold red]❌ {env_check.get('failed_tests', 0)} tests still failing in environment.[/bold red]")

        Prompt.ask("\nPress Enter to return", default="")

    def export_audit_report(self, report: Optional[ReviewReport] = None) -> None:
        """Exports full audit report into dist/reports/ and .context/reviews/."""
        active_report = report or self.current_report or self.engine.load_latest_report()
        if not active_report:
            self.console.print("\n[yellow]⚠️  No audit report to export. Run option 1 first.[/yellow]\n")
            Prompt.ask("Press Enter to return", default="")
            return

        json_path = self.engine.save_report(active_report)
        md_path = os.path.join(self.root_dir, "dist", "reports", "audit_report.md")

        self.console.print("\n[bold green]✓ Reviewer Audit Report successfully exported![/bold green]")
        self.console.print(f"  • [bold white]{os.path.relpath(md_path, self.root_dir)}[/bold white] (Markdown Report)")
        self.console.print(f"  • [bold white]{os.path.relpath(json_path, self.root_dir)}[/bold white] (Full Traceable JSON Data)\n")
        Prompt.ask("Press Enter to return", default="")

    def test_providers_health(self) -> None:
        """Runs connectivity and health diagnostics across all registered reviewer providers."""
        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  🩺 REVIEWER PROVIDER HEALTH & CONNECTIVITY TEST[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")

        all_adapters = ProviderRegistry.all()
        table = Table(box=None, padding=(0, 2), header_style="bold bright_cyan")
        table.add_column("Provider ID", style="bold white", width=18)
        table.add_column("Reviewer Name", style="white", width=28)
        table.add_column("Status", width=16)
        table.add_column("Health Diagnostics / Target Details", style="dim")

        for p_id, adapter_cls in all_adapters.items():
            try:
                adapter_inst = adapter_cls()
                diag = adapter_inst.test_connection()
                if diag.get("ok"):
                    stat_badge = "[green]✓ Connected[/green]"
                else:
                    stat_badge = "[yellow]! Offline[/yellow]"
                table.add_row(
                    p_id,
                    getattr(adapter_cls, "name", p_id),
                    stat_badge,
                    diag.get("message", "N/A")
                )
            except Exception as e:
                table.add_row(
                    p_id,
                    getattr(adapter_cls, "name", p_id),
                    "[red]✗ Error[/red]",
                    str(e)
                )

        self.console.print(Panel(table, border_style="cyan", padding=(1, 2)))
        Prompt.ask("Press Enter to return", default="")
