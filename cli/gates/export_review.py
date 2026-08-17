"""Approval Gate 3: Export Review UI Component."""
import os
import sys
from typing import Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.builder.models import BuildResult
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class ExportReviewGate:
    """Renders Approval Gate 3 (Final Export Review) before project completion."""

    def __init__(self, console: Optional[Console] = None, state_manager: Optional[StateManager] = None):
        self.console = console or Console()
        self.state_mgr = state_manager

    def review_and_confirm(
        self,
        build_result: BuildResult,
        non_interactive: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Render production build artifacts, prompting user to finalize export.
        Returns (approved: bool, feedback: Optional[str]).
        """
        self.console.print("\n[bold green]══════════════════════════════════════════════════════════════[/bold green]")
        self.console.print("[bold bright_green]  🚀 APPROVAL GATE 3: PRODUCTION EXPORT & RELEASE REVIEW[/bold bright_green]")
        self.console.print("[bold green]══════════════════════════════════════════════════════════════[/bold green]\n")

        art_table = Table(box=None, show_header=True, padding=(0, 2))
        art_table.add_column("Artifact File", style="bold white", width=30)
        art_table.add_column("Size", style="cyan", width=12)
        art_table.add_column("Description", style="dim")

        for art in build_result.artifacts:
            size_str = f"{art.size_bytes / 1024:.1f} KB" if art.size_bytes >= 1024 else f"{art.size_bytes} B"
            art_table.add_row(art.path, size_str, art.description)

        panel = Panel(
            art_table,
            title=f"[bold green]Ready for Export: {len(build_result.artifacts)} Release Artifacts ({build_result.elapsed_seconds}s)[/bold green]",
            border_style="green",
            padding=(1, 2)
        )
        self.console.print(panel)

        if non_interactive:
            self.console.print("[green]Non-interactive mode: Release auto-exported and finalized.[/green]")
            if self.state_mgr:
                self.state_mgr.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, "Product Factory execution successfully finalized")
            return True, None

        self.console.print("\n[bold white]Actions:[/bold white] [1] Export & Finalize  [2] Rebuild  [3] Cancel")
        choice = Prompt.ask("Select action", choices=["1", "2", "3"], default="1")

        if choice == "1":
            self.console.print("[bold green]✨ Product Factory Execution Finalized! Artifacts ready in dist/.[/bold green]")
            if self.state_mgr:
                self.state_mgr.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, "Product Factory execution successfully finalized")
            return True, None
        elif choice == "2":
            return False, "rebuild"
        else:
            self.console.print("[dim]Export cancelled.[/dim]")
            return False, None
