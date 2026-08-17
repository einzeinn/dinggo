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
        """Render main ASCII logo and startup environment detection."""
        from core.detector import ProjectDetector

        logo_text = (
            "[bold cyan]  ___  ___ _  _ ___ ___  ___   [/bold cyan]\n"
            "[bold bright_cyan] |   \\|_ _| \\| / __/ __|/ _ \\  [/bold bright_cyan]\n"
            "[bold bright_blue] | |) | || .` | (_| (_ | (_) | [/bold bright_blue]\n"
            "[bold blue] |___/___|_|\\_|\\___\\___|\\___/  [/bold blue]"
        )
        subtitle = "[bold white]🐕 DINGGO PRODUCT FACTORY[/bold white] [dim]· Specification-Driven AI Engine · v0.2.1[/dim]"
        self.console.print(f"{logo_text}\n{subtitle}\n")

        project_name = os.path.basename(self.root_dir)
        self.console.print(f"[bold cyan]Project:[/bold cyan] [bold white]{project_name}[/bold white]")
        self.console.print("[dim]Detecting environment & specifications...[/dim]\n")

        detector = ProjectDetector(self.root_dir)
        detection = detector.detect_all()
        proj = detection.get("project", {})
        providers = detection.get("providers", {})

        git_icon = "[green]✓[/green]" if proj.get("is_git") else "[dim]✗[/dim]"
        spec_icon = "[green]✓[/green]" if proj.get("has_spec") else "[dim]✗[/dim]"
        ctx_icon = "[green]✓[/green]" if proj.get("has_contextix") else "[dim]✗[/dim]"
        active_prov_names = [info["name"] for info in providers.values() if info.get("available")]
        prov_desc = f"AI providers [bold white]({', '.join(active_prov_names)})[/bold white]" if active_prov_names else "AI providers"
        prov_icon = "[green]✓[/green]" if active_prov_names else "[yellow]![/yellow]"
        build_icon = "[green]✓[/green]" if proj.get("build_system") or proj.get("manifests") else "[dim]✗[/dim]"
        test_icon = "[green]✓[/green]" if proj.get("test_framework") or os.path.isdir(os.path.join(self.root_dir, "tests")) else "[dim]✗[/dim]"

        self.console.print(f"  {git_icon} Git repository")
        self.console.print(f"  {spec_icon} Project specification (`spec/`)")
        self.console.print(f"  {ctx_icon} Contextix memory (`.context/`)")
        self.console.print(f"  {prov_icon} {prov_desc}")
        self.console.print(f"  {build_icon} Build system")
        self.console.print(f"  {test_icon} Test system\n")
        self.console.print("[dim]Loading project interface...[/dim]\n")

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
        """Main interactive arrow-key navigation menu loop."""
        from cli.menu_selector import select_menu_option

        while True:
            project_name = self.state_mgr.state.project_name
            phase_str = self.state_mgr.state.phase.value
            status_str = self.state_mgr.state.status.value

            options = [
                ("1. Wizard", "Guided project setup, spec discovery & plan", "wizard"),
                ("2. Execute", "Run tasks, automated tests, repair & validation", "execute"),
                ("3. Settings", "Configure AI models, repair cycles & policies", "settings"),
                ("4. Output", "View builds, artifacts, logs & documentation", "output"),
                ("5. Review", "Run independent reviewer (Codex/AGY/Claude)", "review"),
                ("6. Exit", "Save session state & quit", "exit"),
            ]

            header_extra = f"Project: {project_name}  │  Phase: {phase_str}  │  Status: {status_str}"
            choice = select_menu_option("DINGGO PRODUCT FACTORY", options, header_extra=header_extra)

            if choice in ("exit", None, "6"):
                self.console.print("[bold cyan]🐕 Goodbye! Dinggo session saved.[/bold cyan]")
                break
            elif choice in ("1", "wizard"):
                wizard = ProductFactoryWizard(self.root_dir, console=self.console, state_manager=self.state_mgr)
                wizard.run()
            elif choice in ("2", "execute"):
                self._execute_action()
            elif choice in ("3", "settings"):
                settings = SettingsView(self.root_dir, console=self.console)
                settings.display_menu()
            elif choice in ("4", "output"):
                self._output_action()
            elif choice in ("5", "review"):
                self._review_action()

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
