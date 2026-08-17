"""Live Execution Dashboard & Progress Renderer for Dinggo Product Factory."""
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.planner.task_graph import TaskGraphSchema, TaskNode
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager
from core.orchestrator.scheduler import TaskScheduler
from core.workers.base_worker import ExecutionRecord


class LiveExecutionDashboard:
    """Renders real-time multi-worker task execution progress."""

    def __init__(self, root_dir: str = ".", console: Optional[Console] = None, state_manager: Optional[StateManager] = None):
        self.root_dir = root_dir
        self.console = console or Console()
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.scheduler = TaskScheduler(self.root_dir, state_manager=self.state_mgr)

    def execute_plan(
        self,
        graph: TaskGraphSchema,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> bool:
        """Runs the TaskScheduler with live console progress callbacks."""
        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  🚀 DINGGO PRODUCT FACTORY — MULTI-WORKER EXECUTION[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")

        total_tasks = len(graph.tasks)

        def on_task_start(task: TaskNode, idx: int, total: int):
            pct = int((idx / total) * 100)
            bar_len = 20
            filled = int((pct / 100) * bar_len)
            bar_str = "█" * filled + "░" * (bar_len - filled)

            card_table = Table(box=None, show_header=False, padding=(0, 2))
            card_table.add_column("Key", style="bold cyan", width=16)
            card_table.add_column("Value", style="bold white")

            card_table.add_row("Phase:", "[yellow]IMPLEMENTATION[/yellow]")
            card_table.add_row("Progress:", f"[bold green]{bar_str} {pct}%[/bold green] ({idx}/{total} Tasks)")
            card_table.add_row("Active Task:", f"[bold yellow]{task.id}[/bold yellow] — {task.title}")
            card_table.add_row("Assigned Worker:", f"[bold magenta][{task.worker_type.upper()} WORKER][/bold magenta]")
            card_table.add_row("Target Files:", ", ".join(task.target_files) if task.target_files else "None")
            card_table.add_row("Linked Req:", task.requirement_id or "[dim]Scaffolding/Internal[/dim]")

            self.console.print(Panel(
                card_table,
                title=f"[bold bright_blue]Executing Task {idx}/{total}[/bold bright_blue]",
                border_style="bright_blue",
                padding=(1, 2)
            ))

        def on_task_finish(task: TaskNode, record: ExecutionRecord, idx: int, total: int):
            if record.status == "completed":
                self.console.print(f"[bold green]  ✓ [{task.id}] Completed in {record.elapsed_seconds}s[/bold green] — [dim]{record.output_summary}[/dim]\n")
            else:
                self.console.print(f"[bold red]  ✗ [{task.id}] FAILED:[/bold red] {record.error}\n")

        results = self.scheduler.execute_graph(
            graph=graph,
            spec=spec,
            context=context,
            on_task_start=on_task_start,
            on_task_finish=on_task_finish
        )

        if results["success"]:
            self.console.print(Panel(
                f"[bold green]✓ All {results['total_tasks']} tasks successfully implemented across workers in {results['elapsed_seconds']}s![/bold green]",
                border_style="green"
            ))
            return True
        else:
            self.console.print(Panel(
                f"[bold red]❌ Execution halted on task {results.get('failed_task_id')}: {results.get('error')}[/bold red]",
                border_style="red"
            ))
            return False
