"""Approval Gate 2: Validation Review UI Component."""
import os
import sys
from typing import Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.validation.requirement_validator import ValidationResult
from core.testing.test_runner import TestRunSummary


class ValidationReviewGate:
    """Renders Approval Gate 2 (Validation Review) before build generation."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def review_and_confirm(
        self,
        validation: ValidationResult,
        test_summary: Optional[TestRunSummary] = None,
        non_interactive: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Render specification validation and test results, prompting user to approve build.
        Returns (approved: bool, revision_feedback: Optional[str]).
        """
        self.console.print("\n[bold yellow]══════════════════════════════════════════════════════════════[/bold yellow]")
        self.console.print("[bold bright_yellow]  🛡️  APPROVAL GATE 2: SPECIFICATION VALIDATION REVIEW[/bold bright_yellow]")
        self.console.print("[bold yellow]══════════════════════════════════════════════════════════════[/bold yellow]\n")

        val_table = Table(box=None, show_header=False, padding=(0, 2))
        val_table.add_column("Category", style="bold cyan", width=24)
        val_table.add_column("Status", style="bold white")

        req_status = f"[green]{validation.satisfied_requirements}/{validation.total_requirements} PASS[/green]" if validation.success else f"[red]{validation.satisfied_requirements}/{validation.total_requirements} INCOMPLETE[/red]"
        val_table.add_row("Requirements Coverage:", req_status)
        val_table.add_row("Acceptance Criteria:", f"[green]{validation.satisfied_acceptance_criteria}/{validation.total_acceptance_criteria} PASS[/green]")
        val_table.add_row("Architecture Constraints:", f"[green]{validation.satisfied_architecture_constraints}/{validation.total_architecture_constraints} PASS[/green]")

        if test_summary:
            test_str = f"[green]{test_summary.passed_tests}/{test_summary.total_tests} PASS[/green]" if test_summary.success else f"[red]{test_summary.failed_tests} FAILED[/red]"
            val_table.add_row("Automated Tests:", test_str)

        panel = Panel(
            val_table,
            title="[bold green]Validation & Test Quality Summary[/bold green]" if validation.success else "[bold red]Validation Warnings Detected[/bold red]",
            border_style="green" if validation.success else "red",
            padding=(1, 2)
        )
        self.console.print(panel)

        if non_interactive:
            self.console.print("[green]Non-interactive mode: Build auto-approved.[/green]")
            return True, None

        self.console.print("\n[bold white]Actions:[/bold white] [1] Approve Build  [2] Request Revision  [3] Cancel")
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")

        if choice == "1":
            self.console.print("[bold green]✓ Build Approved! Proceeding to compilation & packaging.[/bold green]")
            return True, None
        elif choice == "2":
            feedback = Prompt.ask("[yellow]Enter revision feedback[/yellow]")
            return False, feedback
        else:
            self.console.print("[dim]Build cancelled.[/dim]")
            return False, None
