import os
import sys
from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, Confirm

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.detector import ProjectDetector
from core.spec.parser import SpecParser
from core.spec.generator import SpecGenerator
from core.spec.models import ProductSpec, DinggoConfig
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.memory import ContextixAdapter, ProjectContext


class ProductFactoryWizard:
    """Step-by-step interactive wizard for initializing and planning a project."""

    def __init__(
        self,
        root_dir: str = ".",
        console: Optional[Console] = None,
        state_manager: Optional[StateManager] = None,
        ollama_client: Optional[Any] = None,
        non_interactive: bool = False
    ):
        self.root_dir = os.path.abspath(root_dir)
        self.console = console or Console()
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.ollama_client = ollama_client
        self.detector = ProjectDetector(self.root_dir)
        self.spec_parser = SpecParser(self.root_dir)
        self.spec_generator = SpecGenerator(self.root_dir)
        self.contextix = ContextixAdapter(ProjectContext(working_dir=self.root_dir))
        self.non_interactive = non_interactive

    def run(self) -> bool:
        """Run the complete guided wizard workflow."""
        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  🐕 DINGGO PRODUCT FACTORY — INITIALIZATION WIZARD[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")

        # Step 1: Project Detection
        proj_info = self.step_1_detect_project()

        # Step 2: Spec Discovery
        spec = self.step_2_spec_discovery(proj_info)
        if not spec:
            self.console.print("[yellow]Wizard aborted at specification step.[/yellow]")
            return False

        # Step 3 & 4: Providers & Setup
        self.step_3_provider_setup()

        # Step 5: Contextix Intelligence Generation
        self.step_5_context_generation()

        # Step 6: Plan Generation & Review Gate 1
        plan_approved = self.step_6_plan_and_review(spec)
        return plan_approved

    def step_1_detect_project(self) -> Dict[str, Any]:
        """Step 1: Detect project repository and frameworks."""
        self.console.print("[bold white]Step 1/6: Project Detection[/bold white]")
        self.state_mgr.transition_to(PipelinePhase.SPEC_DISCOVERY, PipelineStatus.IN_PROGRESS, "Detecting project stack")
        proj = self.detector.detect_project()

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim cyan", width=18)
        table.add_column("Value", style="bold white")

        table.add_row("Project Name:", proj["name"])
        table.add_row("Root Directory:", proj["root_path"])
        table.add_row("Project Type:", proj["type"])
        table.add_row("Git Repository:", "[green]✓ Detected[/green]" if proj["is_git"] else "[dim]Not a git repository[/dim]")
        table.add_row("Languages:", ", ".join(proj["languages"]) if proj["languages"] else "[dim]None detected[/dim]")
        table.add_row("Frameworks:", ", ".join(proj["frameworks"]) if proj["frameworks"] else "[dim]None detected[/dim]")
        table.add_row("Manifests:", ", ".join(proj["manifests"]) if proj["manifests"] else "[dim]None[/dim]")

        self.console.print(Panel(table, border_style="cyan", title="[bold cyan]Project Environment[/bold cyan]"))
        return proj

    def step_2_spec_discovery(self, proj_info: Dict[str, Any]) -> Optional[ProductSpec]:
        """Step 2: Check specification directory, offer creation if missing."""
        self.console.print("\n[bold white]Step 2/6: Specification Discovery[/bold white]")
        if not self.spec_parser.spec_exists():
            self.console.print("[yellow]⚠️  No specification directory ('spec/') found in project root.[/yellow]")
            self.console.print("Dinggo is a Specification-Driven Product Factory and requires structured specs to operate.\n")

            if self.non_interactive:
                init_spec = True
            else:
                init_spec = Confirm.ask("Would you like Dinggo to initialize a standard 'spec/' template?", default=True)

            if init_spec:
                created = self.spec_generator.initialize_spec_directory(project_name=proj_info["name"])
                self.console.print(f"[green]✓ Initialized {len(created)} specification templates in 'spec/' directory.[/green]")
            else:
                return None

        spec = self.spec_parser.parse()
        self.state_mgr.state.stats.requirements_total = len(spec.requirements)
        self.state_mgr.save()

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column("Key", style="dim cyan", width=20)
        table.add_column("Value", style="bold white")

        table.add_row("Product Name:", spec.name)
        table.add_row("Version:", spec.version)
        table.add_row("Requirements Found:", f"[bold green]{len(spec.requirements)} items[/bold green]")
        table.add_row("Architecture Target:", spec.architecture.framework or "[dim]Not specified[/dim]")
        table.add_row("Acceptance Criteria:", f"{len(spec.acceptance_criteria)} items")

        self.console.print(Panel(table, border_style="green", title="[bold green]Specification Overview[/bold green]"))
        return spec

    def step_3_provider_setup(self) -> None:
        """Step 3 & 4: Discover and configure AI providers."""
        self.console.print("\n[bold white]Step 3/6: AI Provider Discovery & Setup[/bold white]")
        providers = self.detector.detect_providers()

        table = Table(show_header=True, header_style="bold cyan", border_style="dim")
        table.add_column("Provider")
        table.add_column("Type")
        table.add_column("Status")

        for key, info in providers.items():
            status = "[green]✓ Ready[/green]" if info.get("available") else "[dim red]✗ Not Detected[/dim red]"
            table.add_row(info["name"], info["type"], status)

        self.console.print(table)

    def step_5_context_generation(self) -> None:
        """Step 5: Run Contextix project intelligence generator."""
        self.console.print("\n[bold white]Step 4/6: Project Intelligence & Context Generation[/bold white]")
        self.console.print("[dim]Analyzing repository structure and documentation graphs via Contextix...[/dim]")
        try:
            res = self.contextix.run_generate()
            if res.get("success"):
                self.console.print("[green]✓ Project context index generated successfully.[/green]")
            else:
                self.console.print(f"[yellow]⚠️  Contextix note: {res.get('error', 'Ready')}[/yellow]")
        except Exception as e:
            self.console.print(f"[dim]Contextix skipped: {e}[/dim]")

    def step_6_plan_and_review(self, spec: ProductSpec) -> bool:
        """Step 6: Generate Execution Plan DAG and present Approval Gate 1."""
        from core.planner import Planner
        from cli.gates.plan_review import PlanReviewGate

        self.console.print("\n[bold white]Step 5/6: Execution Plan Generation[/bold white]")
        self.state_mgr.transition_to(PipelinePhase.PLANNING, PipelineStatus.IN_PROGRESS, "Generating execution plan DAG")
        self.console.print("[cyan]Planner is constructing task dependency graph from specification...[/cyan]")

        planner = Planner(ollama_client=self.ollama_client)
        plan_res = planner.create_product_task_graph(spec)
        graph = plan_res["graph"]

        self.state_mgr.state.active_plan = graph.model_dump(mode="json")
        self.state_mgr.state.stats.tasks_total = len(graph.tasks)
        self.state_mgr.transition_to(PipelinePhase.APPROVAL_GATE_1, PipelineStatus.AWAITING_APPROVAL, "Awaiting Plan Approval")

        # Step 7: Approval Gate 1 Review Panel
        gate = PlanReviewGate(console=self.console)
        approved, feedback = gate.review_and_confirm(graph, non_interactive=self.non_interactive)

        if approved:
            self.state_mgr.transition_to(PipelinePhase.IMPLEMENTING, PipelineStatus.IN_PROGRESS, "Plan approved, ready to execute", can_resume=True)
            return True
        elif feedback:
            self.console.print(f"[yellow]Plan revision requested: {feedback}[/yellow]")
            self.state_mgr.transition_to(PipelinePhase.PLANNING, PipelineStatus.PAUSED, f"Revision requested: {feedback}", can_resume=True)
            return False
        else:
            self.state_mgr.transition_to(PipelinePhase.IDLE, PipelineStatus.IDLE, "Wizard cancelled")
            return False
