import os
import sys
import yaml
from typing import Dict, Any, Optional
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

from core.spec.parser import SpecParser
from core.spec.models import DinggoConfig
from core.detector import ProjectDetector


class SettingsView:
    """Manages viewing and modifying dinggo.yaml configuration interactively."""

    def __init__(self, root_dir: str = ".", console: Optional[Console] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.console = console or Console()
        self.spec_parser = SpecParser(self.root_dir)
        self.detector = ProjectDetector(self.root_dir)
        self.config: DinggoConfig = self.spec_parser.load_config()

    def display_menu(self) -> None:
        """Interactive settings configuration loop."""
        while True:
            self.console.print()
            table = Table(title="🛠️  DINGGO PRODUCT FACTORY — SETTINGS", border_style="cyan", show_lines=False)
            table.add_column("No", style="bold cyan", width=4)
            table.add_column("Category", style="bold white", width=22)
            table.add_column("Current Configuration", style="dim white")

            table.add_row("1", "AI Providers", f"Reviewer: {self.config.review.default_provider.upper()} | Mode: {self.config.mode}")
            table.add_row("2", "Execution & Repair", f"Auto-Repair: {'ON' if self.config.repair.enabled else 'OFF'} | Max Attempts: {self.config.repair.max_attempts}")
            table.add_row("3", "Approval Gates", f"Plan: {self.config.approval.plan} | Build: {self.config.approval.build} | Export: {self.config.approval.export}")
            table.add_row("4", "Security Policy", f"Critical: {self.config.security.critical_failure.upper()} | High: {self.config.security.high_failure.upper()}")
            table.add_row("5", "Independent Review", f"Required: {self.config.review.required} | Max Cycles: {self.config.review.max_repair_cycles}")
            table.add_row("6", "Detect Providers Again", "Scan local system for Ollama / Codex / Claude CLI")
            table.add_row("0", "Back to Main Menu", "Save & return")

            self.console.print(table)
            choice = Prompt.ask("[bold cyan]Select setting to edit[/bold cyan]", choices=["1", "2", "3", "4", "5", "6", "0"], default="0")

            if choice == "0":
                self.save_config()
                break
            elif choice == "1":
                self._edit_providers()
            elif choice == "2":
                self._edit_execution()
            elif choice == "3":
                self._edit_approval()
            elif choice == "4":
                self._edit_security()
            elif choice == "5":
                self._edit_review()
            elif choice == "6":
                self._rescan_providers()

    def _edit_providers(self) -> None:
        """Edit default provider and execution mode."""
        self.console.print("\n[bold white]Configure AI Providers & Mode:[/bold white]")
        mode = Prompt.ask("Execution Mode", choices=["safe", "autonomous", "governed"], default=self.config.mode)
        self.config.mode = mode
        provider = Prompt.ask("Default Independent Reviewer", choices=["codex", "claude", "ollama", "gemini"], default=self.config.review.default_provider)
        self.config.review.default_provider = provider
        self.console.print("[green]✓ Providers updated.[/green]")

    def _edit_execution(self) -> None:
        """Edit self-repair settings."""
        self.console.print("\n[bold white]Configure Execution & Self-Repair:[/bold white]")
        enabled = Prompt.ask("Enable Auto-Repair?", choices=["yes", "no"], default="yes" if self.config.repair.enabled else "no") == "yes"
        attempts = int(Prompt.ask("Max Repair Attempts", default=str(self.config.repair.max_attempts)))
        self.config.repair.enabled = enabled
        self.config.repair.max_attempts = attempts
        self.console.print("[green]✓ Execution settings updated.[/green]")

    def _edit_approval(self) -> None:
        """Edit approval gate requirements."""
        self.console.print("\n[bold white]Configure Approval Gates:[/bold white]")
        plan = Prompt.ask("Require Approval before Plan Execution?", choices=["yes", "no"], default="yes" if self.config.approval.plan else "no") == "yes"
        build = Prompt.ask("Require Approval before Build?", choices=["yes", "no"], default="yes" if self.config.approval.build else "no") == "yes"
        export = Prompt.ask("Require Approval before Final Export?", choices=["yes", "no"], default="yes" if self.config.approval.export else "no") == "yes"
        self.config.approval.plan = plan
        self.config.approval.build = build
        self.config.approval.export = export
        self.console.print("[green]✓ Approval gates updated.[/green]")

    def _edit_security(self) -> None:
        """Edit security threshold policies."""
        self.console.print("\n[bold white]Configure Security Policies:[/bold white]")
        crit = Prompt.ask("Action on Critical Vulnerability", choices=["block", "warn", "ignore"], default=self.config.security.critical_failure)
        high = Prompt.ask("Action on High Vulnerability", choices=["block", "warn", "ignore"], default=self.config.security.high_failure)
        self.config.security.critical_failure = crit
        self.config.security.high_failure = high
        self.console.print("[green]✓ Security policies updated.[/green]")

    def _edit_review(self) -> None:
        """Edit independent review configuration."""
        self.console.print("\n[bold white]Configure Independent Reviewer:[/bold white]")
        req = Prompt.ask("Require Independent Review before release?", choices=["yes", "no"], default="yes" if self.config.review.required else "no") == "yes"
        auto_rev = Prompt.ask("Automatically revise code on reviewer findings?", choices=["yes", "no"], default="yes" if self.config.review.auto_revision else "no") == "yes"
        cycles = int(Prompt.ask("Max Review-Repair Cycles", default=str(self.config.review.max_repair_cycles)))
        self.config.review.required = req
        self.config.review.auto_revision = auto_rev
        self.config.review.max_repair_cycles = cycles
        self.console.print("[green]✓ Reviewer settings updated.[/green]")

    def _rescan_providers(self) -> None:
        """Scan system for available AI providers."""
        self.console.print("\n[bold cyan]Scanning for available AI Providers...[/bold cyan]")
        providers = self.detector.detect_providers()
        table = Table(border_style="dim", show_lines=True)
        table.add_column("Provider", style="bold white")
        table.add_column("Type", style="dim")
        table.add_column("Status", style="bold")
        table.add_column("Details")

        for key, info in providers.items():
            status = "[green]✓ Available[/green]" if info.get("available") else "[red]✗ Not Detected[/red]"
            details = ", ".join(info.get("models", [])) if info.get("models") else ("CLI executable found" if info.get("available") else "Not found in PATH")
            table.add_row(info["name"], info["type"], status, details)

        self.console.print(table)
        Prompt.ask("\nPress Enter to return", default="")

    def save_config(self) -> None:
        """Save configuration to dinggo.yaml."""
        cfg_path = os.path.join(self.root_dir, "dinggo.yaml")
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config.model_dump(mode="json"), f, sort_keys=False)
            self.console.print("[green]✓ Configuration saved to dinggo.yaml[/green]")
        except Exception as e:
            self.console.print(f"[red]Failed to save configuration: {e}[/red]")
