"""Product Factory Pipeline Orchestrator for Dinggo."""
import os
from typing import Optional, Dict, Any
from rich.console import Console

from core.spec.parser import SpecParser
from core.spec.generator import SpecGenerator
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.planner.planner_engine import Planner
from core.orchestrator.scheduler import TaskScheduler
from core.testing.test_runner import TestRunner
from core.repair.repair_engine import RepairEngine
from core.validation.requirement_validator import RequirementValidator
from core.builder.builder_engine import BuildEngine
from core.reviewer.review_engine import ReviewEngine
from cli.gates.plan_review import PlanReviewGate
from cli.gates.validation_review import ValidationReviewGate
from cli.gates.export_review import ExportReviewGate


class ProductFactoryPipeline:
    """Master pipeline executing the full 8-phase AI Product Factory lifecycle."""

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
        self.client = ollama_client
        self.non_interactive = non_interactive

        self.spec_parser = SpecParser(self.root_dir)
        self.spec_generator = SpecGenerator(self.root_dir)
        self.planner = Planner(ollama_client=self.client)
        self.scheduler = TaskScheduler(self.root_dir, state_manager=self.state_mgr, ollama_client=self.client)
        self.repair_engine = RepairEngine(self.root_dir, state_manager=self.state_mgr, ollama_client=self.client)
        self.validator = RequirementValidator(self.root_dir)
        self.builder = BuildEngine(self.root_dir, state_manager=self.state_mgr)
        self.reviewer = ReviewEngine(self.root_dir, state_manager=self.state_mgr)

    def run_pipeline(self, auto_approve: bool = False) -> bool:
        """
        Executes full product factory lifecycle:
        1. Spec Parse/Gen -> 2. Plan DAG -> 3. Gate 1 -> 4. Execute ->
        5. Test & Repair -> 6. Gate 2 -> 7. Build -> 8. Review -> 9. Gate 3 (Export)
        """
        is_headless = self.non_interactive or auto_approve

        # Step 1: Ensure Spec
        if not self.spec_parser.has_specs():
            self.console.print("[yellow]No spec/ directory found. Generating default specifications...[/yellow]")
            self.spec_generator.generate_defaults("Product Factory Application")

        spec = self.spec_parser.parse()
        self.state_mgr.state.project_name = spec.name
        self.state_mgr.state.stats.requirements_total = len(spec.requirements)
        self.state_mgr.save()

        # Step 2: Generate or Resume Plan DAG
        if self.state_mgr.can_resume() and self.state_mgr.state.active_plan:
            self.console.print("\n[bold cyan]Phase 1/6: Resuming active Task Graph DAG...[/bold cyan]")
            from core.planner.task_graph import TaskGraphSchema
            graph = TaskGraphSchema(**self.state_mgr.state.active_plan)
        else:
            self.console.print("\n[bold cyan]Phase 1/6: Constructing Task Graph DAG...[/bold cyan]")
            plan_res = self.planner.create_product_task_graph(spec)
            graph = plan_res["graph"]
            self.state_mgr.state.active_plan = graph.model_dump(mode="json")
            self.state_mgr.state.stats.tasks_total = len(graph.tasks)
            self.state_mgr.save()

            # Step 3: Approval Gate 1 (Plan Review)
            gate1 = PlanReviewGate(console=self.console)
            app1, _ = gate1.review_and_confirm(graph, non_interactive=is_headless)
            if not app1:
                self.console.print("[red]Plan rejected. Pipeline halted.[/red]")
                return False

        # Step 4: Multi-Worker Implementation
        self.console.print("\n[bold cyan]Phase 2/6: Executing Tasks via Multi-Worker Engine...[/bold cyan]")
        exec_res = self.scheduler.execute_graph(graph, spec=spec)
        if not exec_res["success"]:
            self.console.print(f"[red]Task execution failed on {exec_res.get('failed_task_id')}: {exec_res.get('error')}[/red]")
            return False

        # Step 5: Automated Testing & Closed-Loop Repair
        self.console.print("\n[bold cyan]Phase 3/6: Running Automated Tests & Self-Repair...[/bold cyan]")
        repair_res = self.repair_engine.run_repair_loop()
        if not repair_res["success"]:
            self.console.print(f"[red]Automated testing & self-repair failed: {repair_res.get('error')}[/red]")
            return False

        # Step 6: Requirement Traceability Validation & Gate 2
        self.console.print("\n[bold cyan]Phase 4/6: Validating Specification Traceability...[/bold cyan]")
        val_res = self.validator.validate(spec, state=self.state_mgr.state)
        gate2 = ValidationReviewGate(console=self.console)
        app2, _ = gate2.review_and_confirm(val_res, non_interactive=is_headless)
        if not app2:
            self.console.print("[red]Specification validation rejected. Pipeline halted.[/red]")
            return False

        # Step 7: Production Build & Packaging
        self.console.print("\n[bold cyan]Phase 5/6: Building Production Release Packages...[/bold cyan]")
        build_res = self.builder.build_and_export(spec=spec)
        if not build_res.success:
            self.console.print(f"[red]Build failed: {build_res.error}[/red]")
            return False

        # Step 8: Independent Reviewer & Gate 3 (Export)
        self.console.print("\n[bold cyan]Phase 6/6: Independent Code Audit & Final Export...[/bold cyan]")
        rev_res = self.reviewer.run_review_loop(spec=spec)

        gate3 = ExportReviewGate(console=self.console, state_manager=self.state_mgr)
        app3, _ = gate3.review_and_confirm(build_res, non_interactive=is_headless)
        if not app3:
            self.console.print("[red]Final export rejected. Pipeline halted.[/red]")
            return False

        self.console.print("\n[bold green]🎉 SUCCESS: Complete Product Factory Pipeline finished successfully![/bold green]")
        return True
