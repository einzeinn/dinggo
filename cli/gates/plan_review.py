"""Approval Gate 1: Plan Review UI Component."""
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

from core.planner.task_graph import TaskGraphSchema


class PlanReviewGate:
    """Renders Approval Gate 1 (Plan Review) and collects user approval/revisions."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def review_and_confirm(
        self,
        graph: TaskGraphSchema,
        non_interactive: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Render plan details and prompt user for approval.
        Returns (approved: bool, revision_feedback: Optional[str]).
        """
        self.console.print("\n[bold yellow]══════════════════════════════════════════════════════════════[/bold yellow]")
        self.console.print("[bold bright_yellow]  🛡️  APPROVAL GATE 1: EXECUTION PLAN & DAG REVIEW[/bold bright_yellow]")
        self.console.print("[bold yellow]══════════════════════════════════════════════════════════════[/bold yellow]\n")

        # 1. Summary Overview
        summary_table = Table(box=None, show_header=False, padding=(0, 2))
        summary_table.add_column("Metric", style="bold cyan", width=22)
        summary_table.add_column("Value", style="bold white")

        summary_table.add_row("Project Name:", graph.project_name)
        summary_table.add_row("Target Architecture:", graph.architecture)
        summary_table.add_row("Target Database:", graph.database)
        summary_table.add_row("Total DAG Tasks:", f"[bold green]{len(graph.tasks)} tasks[/bold green]")
        summary_table.add_row("Requirements Covered:", f"[bold green]{len(graph.requirements_coverage)} requirements mapped[/bold green]")

        self.console.print(Panel(summary_table, border_style="cyan", title="[bold cyan]Plan Architecture Overview[/bold cyan]"))

        # 2. Detailed Task DAG Table
        task_table = Table(title="📋  TASK DEPENDENCY GRAPH (TOPOLOGICAL ORDER)", border_style="dim", show_lines=True)
        task_table.add_column("ID", style="bold yellow", width=10)
        task_table.add_column("Task Title", style="bold white")
        task_table.add_column("Worker", style="cyan", width=12)
        task_table.add_column("Req ID", style="magenta", width=12)
        task_table.add_column("Target Files", style="dim", width=24)
        task_table.add_column("Depends On", style="dim yellow", width=16)

        topological_tasks = graph.get_topological_order()
        for task in topological_tasks:
            worker_badge = f"[{task.worker_type}]"
            req_str = task.requirement_id or "[dim]N/A[/dim]"
            files_str = ", ".join(task.target_files) if task.target_files else "[dim]None[/dim]"
            deps_str = ", ".join(task.depends_on) if task.depends_on else "[green]root[/green]"

            task_table.add_row(
                task.id,
                task.title,
                worker_badge,
                req_str,
                files_str,
                deps_str
            )

        self.console.print(task_table)

        if non_interactive:
            self.console.print("[green]Non-interactive mode: Plan auto-approved.[/green]")
            return True, None

        self.console.print("\n[bold white]Actions:[/bold white] [1] Approve Plan & Begin Execution  [2] Request Revision  [3] Cancel")
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")

        if choice == "1":
            self.console.print("[bold green]✓ Execution Plan Approved![/bold green]")
            return True, None
        elif choice == "2":
            feedback = Prompt.ask("[yellow]Enter revision feedback for Planner[/yellow]")
            return False, feedback
        else:
            self.console.print("[dim]Plan cancelled.[/dim]")
            return False, None
