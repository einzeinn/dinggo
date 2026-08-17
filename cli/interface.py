import os
import sys
from typing import Optional
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

from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from cli.wizard import ProductFactoryWizard
from cli.settings_view import SettingsView


class ProductFactoryInterface:
    """Main interactive terminal shell for Dinggo Product Factory."""

    def __init__(self, root_dir: str = ".", console: Optional[Console] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.console = console or Console()
        self.state_mgr = StateManager(self.root_dir)

    def start(self) -> None:
        """Entry point for the interactive loop."""
        self.display_header()

        # Check for resumable session
        if self.state_mgr.can_resume():
            self.handle_resumable_session()

        # Main interactive navigation loop
        self.menu_loop()

    def display_header(self) -> None:
        """Render main ASCII logo and subtitle."""
        logo_text = (
            "[bold cyan]  ___  ___ _  _ ___ ___  ___   [/bold cyan]\n"
            "[bold bright_cyan] |   \\|_ _| \\| / __/ __|/ _ \\  [/bold bright_cyan]\n"
            "[bold bright_blue] | |) | || .` | (_| (_ | (_) | [/bold bright_blue]\n"
            "[bold blue] |___/___|_|\\_|\\___\\___|\\___/  [/bold blue]"
        )
        subtitle = "[bold white]🐕 DINGGO PRODUCT FACTORY[/bold white] [dim]· Specification-Driven AI Engine · v0.2.0[/dim]"
        self.console.print(f"{logo_text}\n{subtitle}\n")

    def handle_resumable_session(self) -> None:
        """Prompt developer when an unfinished session is detected."""
        sess = self.state_mgr.state.session
        phase = self.state_mgr.state.phase.value
        status = self.state_mgr.state.status.value

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="bold yellow", width=16)
        table.add_column("Value", style="bold white")

        table.add_row("Session ID:", sess.id)
        table.add_row("Last Phase:", f"[cyan]{phase}[/cyan] ({status})")
        table.add_row("Active Task:", sess.active_task_id or "N/A")
        table.add_row("Repair Cycle:", f"{sess.repair_cycle}/{sess.max_repair_cycles}")
        table.add_row("Last Message:", self.state_mgr.state.last_message)

        panel = Panel(
            table,
            title="[bold yellow]⚡ RESUMABLE SESSION FOUND[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print("[bold white]Options:[/bold white] [1] Resume Session  [2] Restart Fresh  [3] Continue to Menu")
        choice = Prompt.ask("Choose option", choices=["1", "2", "3"], default="1")

        if choice == "1":
            self.console.print(f"[bold green]Resuming session in phase: {phase}...[/bold green]")
            if phase in (PipelinePhase.PLANNING.value, PipelinePhase.APPROVAL_GATE_1.value):
                wizard = ProductFactoryWizard(self.root_dir, console=self.console, state_manager=self.state_mgr)
                wizard.run()
            elif phase in (PipelinePhase.IMPLEMENTING.value, PipelinePhase.TESTING.value, PipelinePhase.REPAIRING.value):
                self.console.print("[cyan]Routing to Execution Engine...[/cyan]")
        elif choice == "2":
            self.state_mgr.reset()
            self.console.print("[green]Session reset to clean IDLE state.[/green]")

    def menu_loop(self) -> None:
        """Main navigation menu loop."""
        while True:
            self._render_status_menu()
            choice = Prompt.ask(
                "[bold cyan]Select action[/bold cyan]",
                choices=["1", "2", "3", "4", "5", "6", "exit", "quit"],
                default="1"
            )

            if choice in ("6", "exit", "quit"):
                self.console.print("[bold cyan]🐕 Goodbye! Dinggo session saved.[/bold cyan]")
                break
            elif choice == "1":
                wizard = ProductFactoryWizard(self.root_dir, console=self.console, state_manager=self.state_mgr)
                wizard.run()
            elif choice == "2":
                self._execute_action()
            elif choice == "3":
                settings = SettingsView(self.root_dir, console=self.console)
                settings.display_menu()
            elif choice == "4":
                self._output_action()
            elif choice == "5":
                self._review_action()

    def _render_status_menu(self) -> None:
        """Display the structured status menu card."""
        project_name = self.state_mgr.state.project_name
        phase_str = self.state_mgr.state.phase.value
        status_str = self.state_mgr.state.status.value

        menu_items = (
            "  [bold cyan]> 1. Wizard[/bold cyan]      [dim]— Guided project setup, spec discovery & plan[/dim]\n"
            "    [bold white]2. Execute[/bold white]     [dim]— Run tasks, automated tests, repair & validation[/dim]\n"
            "    [bold white]3. Settings[/bold white]    [dim]— Configure AI models, repair cycles & policies[/dim]\n"
            "    [bold white]4. Output[/bold white]      [dim]— View builds, artifacts, logs & documentation[/dim]\n"
            "    [bold white]5. Review[/bold white]      [dim]— Run independent reviewer (Codex/Claude)[/dim]\n"
            "    [bold white]6. Exit[/bold white]        [dim]— Save session state & quit[/dim]\n"
            "  ─────────────────────────────────────────────────────────────\n"
            f"  [dim]Project:[/dim] [bold white]{project_name}[/bold white]  │  "
            f"[dim]Phase:[/dim] [bold cyan]{phase_str}[/bold cyan]  │  "
            f"[dim]Status:[/dim] [bold green]{status_str}[/bold green]"
        )

        self.console.print(Panel(
            Text.from_markup(menu_items),
            title="[bold bright_cyan]DINGGO PRODUCT FACTORY[/bold bright_cyan]",
            border_style="bright_cyan",
            padding=(1, 2)
        ))

    def _execute_action(self) -> None:
        """Handler for option 2: Execute."""
        if not self.state_mgr.state.active_plan:
            self.console.print("[yellow]⚠️  No active plan found. Please run the Wizard first (Option 1).[/yellow]")
            return

        from core.planner.task_graph import TaskGraphSchema
        from cli.execution_view import LiveExecutionDashboard
        from core.spec.parser import SpecParser

        try:
            graph = TaskGraphSchema(**self.state_mgr.state.active_plan)
            spec = SpecParser(self.root_dir).parse()
            dashboard = LiveExecutionDashboard(self.root_dir, console=self.console, state_manager=self.state_mgr)
            dashboard.execute_plan(graph=graph, spec=spec)
        except Exception as e:
            self.console.print(f"[red]Error initiating execution: {e}[/red]")

    def _output_action(self) -> None:
        """Handler for option 4: Output."""
        self.console.print("\n[bold cyan]📦 PRODUCT FACTORY OUTPUTS & ARTIFACTS[/bold cyan]")
        dist_dir = os.path.join(self.root_dir, "dist")
        if os.path.isdir(dist_dir):
            files = os.listdir(dist_dir)
            self.console.print(f"[green]Found {len(files)} items in dist/:[/green] {', '.join(files)}")
        else:
            self.console.print("[dim]No dist/ directory generated yet. Build and export to generate artifacts.[/dim]")

        # Show stats
        stats = self.state_mgr.state.stats
        self.console.print(f"\n[dim]Requirements Total:[/dim] {stats.requirements_total} | [dim]Tasks Completed:[/dim] {stats.tasks_completed}/{stats.tasks_total} | [dim]Tests Passed:[/dim] {stats.tests_passed}/{stats.tests_total}")
        Prompt.ask("\nPress Enter to return", default="")

    def _review_action(self) -> None:
        """Handler for option 5: Review."""
        from cli.review_view import ReviewDashboard
        dashboard = ReviewDashboard(self.root_dir, console=self.console, state_manager=self.state_mgr)
        dashboard.display_and_run()
        Prompt.ask("\nPress Enter to return", default="")
