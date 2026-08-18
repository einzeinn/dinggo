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
        subtitle = "[bold white]🐕 DINGGO PRODUCT FACTORY[/bold white] [dim]· Specification-Driven AI Engine · v0.3.0[/dim]"
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
        """Handler for option 4: Output - Displays workspace files, dist packages, and allows building."""
        from rich.table import Table
        from rich.panel import Panel
        from core.builder.builder_engine import BuildEngine
        from core.spec.parser import SpecParser

        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  📦 PRODUCT FACTORY OUTPUTS & ARTIFACTS[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")

        # 1. Inspect Generated Source Files from Active Plan / Workspace
        plan_data = self.state_mgr.state.active_plan or {}
        tasks = plan_data.get("tasks", [])
        generated_files = []
        for t in tasks:
            for fpath in t.get("target_files", []):
                if fpath not in generated_files:
                    generated_files.append(fpath)

        src_table = Table(title="[bold green]🛠 Generated Source Files & Modules[/bold green]", box=None, padding=(0, 2))
        src_table.add_column("File Path", style="bold white")
        src_table.add_column("Status", style="cyan")
        src_table.add_column("Size", style="dim")

        found_src_count = 0
        for rel_f in generated_files:
            full_f = os.path.join(self.root_dir, rel_f)
            if os.path.isfile(full_f):
                found_src_count += 1
                size_kb = round(os.path.getsize(full_f) / 1024, 2)
                src_table.add_row(f"📄 {rel_f}", "[green]✓ Created (In Workspace)[/green]", f"{size_kb} KB")
            else:
                src_table.add_row(f"📄 {rel_f}", "[dim yellow]Pending / Not created[/dim yellow]", "-")

        if not generated_files:
            # Fallback scan for common source directories
            for scan_dir in ("src", "app", "lib", "models", "routers", "tests"):
                full_sd = os.path.join(self.root_dir, scan_dir)
                if os.path.isdir(full_sd):
                    for r, _, fls in os.walk(full_sd):
                        for fl in fls:
                            rf = os.path.relpath(os.path.join(r, fl), self.root_dir)
                            size_kb = round(os.path.getsize(os.path.join(r, fl)) / 1024, 2)
                            src_table.add_row(f"📄 {rf}", "[green]✓ Found[/green]", f"{size_kb} KB")
                            found_src_count += 1

        if found_src_count > 0:
            self.console.print(Panel(src_table, border_style="green", padding=(1, 2)))
        else:
            self.console.print("[dim]No generated source files detected in workspace yet.[/dim]\n")

        # 2. Inspect Distribution Packages (dist/)
        dist_dir = os.path.join(self.root_dir, "dist")
        has_dist = os.path.isdir(dist_dir) and len(os.listdir(dist_dir)) > 0

        if has_dist:
            dist_table = Table(title="[bold cyan]📦 Production Release Packages (dist/)[/bold cyan]", box=None, padding=(0, 2))
            dist_table.add_column("Artifact", style="bold white")
            dist_table.add_column("Type", style="magenta")
            dist_table.add_column("Size", style="dim")

            for item in sorted(os.listdir(dist_dir)):
                item_path = os.path.join(dist_dir, item)
                if os.path.isfile(item_path):
                    sz = round(os.path.getsize(item_path) / 1024, 2)
                    art_type = "Archive (.zip)" if item.endswith(".zip") else ("Config" if item.endswith((".yml", ".yaml", ".json")) else "Container")
                    dist_table.add_row(f"🎁 dist/{item}", art_type, f"{sz} KB")
                elif os.path.isdir(item_path):
                    sub_count = len(os.listdir(item_path))
                    dist_table.add_row(f"📁 dist/{item}/", "Directory", f"{sub_count} items")

            self.console.print(Panel(dist_table, border_style="cyan", padding=(1, 2)))
        else:
            self.console.print(Panel(
                "[yellow]ℹ️  Production packages (`dist/`) have not been compiled yet.[/yellow]\n"
                "[dim]Source files are in workspace. Run 'Build & Export' to generate release archives, Dockerfile, and docs into dist/.[/dim]",
                title="[bold yellow]Release Packaging[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            ))

        # Show pipeline stats
        stats = self.state_mgr.state.stats
        self.console.print(f"\n[dim]Requirements Total:[/dim] {stats.requirements_total} | [dim]Tasks Completed:[/dim] {stats.tasks_completed}/{stats.tasks_total} | [dim]Tests Passed:[/dim] {stats.tests_passed}/{stats.tests_total}\n")

        # Interactive Options inside Output View
        self.console.print("[bold white]Actions:[/bold white] [1] Build & Export to dist/ now  [2] Return to Menu")
        choice = Prompt.ask("Choose action", choices=["1", "2"], default="2")

        if choice == "1":
            self.console.print("\n[bold cyan]🚀 Building production packages and export artifacts...[/bold cyan]")
            spec_parser = SpecParser(self.root_dir)
            spec = spec_parser.parse() if spec_parser.has_specs() else None
            builder = BuildEngine(self.root_dir, state_manager=self.state_mgr)
            build_res = builder.build_and_export(spec=spec)

            if build_res.success:
                self.console.print(f"[bold green]✓ Build & Export successful! Generated {len(build_res.artifacts)} artifacts in dist/ ({build_res.elapsed_seconds}s)[/bold green]")
                for art in build_res.artifacts:
                    self.console.print(f"  • [bold white]{art.path}[/bold white] — [dim]{art.description}[/dim] ({round(art.size_bytes / 1024, 2)} KB)")
            else:
                self.console.print(f"[bold red]❌ Build failed: {build_res.error}[/bold red]")

            Prompt.ask("\nPress Enter to return", default="")


    def _review_action(self) -> None:
        """Handler for option 5: Review - Launches Reviewer Hub."""
        from cli.review_view import ReviewDashboard
        dashboard = ReviewDashboard(self.root_dir, console=self.console, state_manager=self.state_mgr)
        dashboard.display_menu()
