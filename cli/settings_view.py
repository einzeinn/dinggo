import os
import sys
import yaml
import time
import urllib.request
import json
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from core.spec.parser import SpecParser
from core.spec.models import DinggoConfig
from core.detector import ProjectDetector
from cli.menu_selector import select_menu_option


class SettingsView:
    """Manages viewing and modifying dinggo.yaml configuration interactively with arrow-key menus."""

    def __init__(self, root_dir: str = ".", console: Optional[Console] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.console = console or Console()
        self.spec_parser = SpecParser(self.root_dir)
        self.detector = ProjectDetector(self.root_dir)
        self.config: DinggoConfig = self.spec_parser.load_config()

    def display_menu(self) -> None:
        """Main interactive settings configuration loop with arrow-key navigation."""
        while True:
            prov_status = self._get_active_provider_status()
            repair_status = f"{'ON' if self.config.repair.enabled else 'OFF'} (Max {self.config.repair.max_attempts})"
            approval_status = f"Plan:{'✓' if self.config.approval.plan else '✗'} Build:{'✓' if self.config.approval.build else '✗'} Export:{'✓' if self.config.approval.export else '✗'}"
            sec_status = f"Crit:{self.config.security.critical_failure.upper()} High:{self.config.security.high_failure.upper()}"
            rev_status = f"{'ON' if self.config.review.required else 'OFF'} ({self.config.review.default_provider.upper()}, Max {self.config.review.max_repair_cycles} cycles)"

            options = [
                ("1. AI Providers", f"Default: {self.config.review.default_provider.upper()} · Status: {prov_status}", "providers"),
                ("2. Execution & Repair", f"Self-repair: {repair_status}", "execution"),
                ("3. Approval Gates", f"Gates: {approval_status}", "approval"),
                ("4. Security Policy", f"Thresholds: {sec_status}", "security"),
                ("5. Reviewer Loop", f"Independent review: {rev_status}", "review"),
                ("6. Test Connections", "Live ping & capability diagnostic for all AI providers", "diagnostic"),
                ("0. Save & Return", "Write changes to dinggo.yaml and return to main menu", "save_exit"),
            ]

            header_extra = f"Config: dinggo.yaml  │  Mode: {self.config.mode.upper()}  │  Reviewer: {self.config.review.default_provider.upper()}"
            choice = select_menu_option("DINGGO PRODUCT FACTORY — SETTINGS", options, header_extra=header_extra)

            if choice in ("save_exit", "0", None):
                self.save_config()
                break
            elif choice == "providers":
                self._edit_providers()
            elif choice == "execution":
                self._edit_execution()
            elif choice == "approval":
                self._edit_approval()
            elif choice == "security":
                self._edit_security()
            elif choice == "review":
                self._edit_review()
            elif choice == "diagnostic":
                self._test_all_connections()

    def _get_active_provider_status(self) -> str:
        """Check if current default provider is ready."""
        providers = self.detector.detect_providers()
        def_prov = self.config.review.default_provider.lower().strip()
        info = providers.get(def_prov, {})
        if info.get("available"):
            return "[green]Connected ✓[/green]"
        return "[yellow]Not Detected ✗[/yellow]"

    def _edit_providers(self) -> None:
        """Interactive selection for default AI provider and execution mode."""
        providers = self.detector.detect_providers()

        while True:
            prov_opts = []
            for p_id, p_info in providers.items():
                status = "[green]✓ Ready[/green]" if p_info.get("available") else "[dim red]✗ Not Detected[/dim red]"
                is_active = " [bold cyan](ACTIVE)[/bold cyan]" if p_id == self.config.review.default_provider else ""
                detail = p_info.get("path") or (f"{len(p_info.get('models', []))} models" if p_info.get("models") else p_info["type"])
                prov_opts.append((f"{p_info['name']}{is_active}", f"{status} — {detail}", f"set_prov_{p_id}"))

            prov_opts.append(("Execution Mode", f"Current: {self.config.mode.upper()} (Safe, Autonomous, Governed)", "set_mode"))
            prov_opts.append(("Back", "Return to Settings Menu", "back"))

            choice = select_menu_option("CONFIGURE AI PROVIDERS & MODE", prov_opts)
            if not choice or choice == "back":
                break
            elif choice.startswith("set_prov_"):
                chosen_id = choice.replace("set_prov_", "")
                self.config.review.default_provider = chosen_id
                self.console.print(f"[bold green]✓ Default AI Reviewer set to: {chosen_id.upper()}[/bold green]")
            elif choice == "set_mode":
                mode_opts = [
                    ("1. Safe Mode", "All approval gates active, human-in-the-loop on each phase", "safe"),
                    ("2. Autonomous Mode", "Auto-approves non-critical gates and tests automatically", "autonomous"),
                    ("3. Governed Mode", "Strict compliance gates, requires reviewer sign-off", "governed"),
                    ("Back", "Cancel mode change", "cancel")
                ]
                m_choice = select_menu_option("SELECT FACTORY EXECUTION MODE", mode_opts)
                if m_choice and m_choice != "cancel":
                    self.config.mode = m_choice
                    self.console.print(f"[bold green]✓ Execution mode set to: {m_choice.upper()}[/bold green]")

    def _edit_execution(self) -> None:
        """Interactive settings for automated test repair."""
        while True:
            rep_opts = [
                (f"Auto-Repair Engine: {'[green]ENABLED[/green]' if self.config.repair.enabled else '[red]DISABLED[/red]'}", "Toggle automated error diagnosis and patch loop", "toggle_repair"),
                (f"Max Repair Attempts: {self.config.repair.max_attempts}", "Maximum diagnosis-patch-retest retry cycles before pause", "set_attempts"),
                ("Back", "Return to Settings Menu", "back")
            ]
            choice = select_menu_option("EXECUTION & SELF-REPAIR SETTINGS", rep_opts)
            if not choice or choice == "back":
                break
            elif choice == "toggle_repair":
                self.config.repair.enabled = not self.config.repair.enabled
            elif choice == "set_attempts":
                att_opts = [
                    ("1 Attempt", "No retries, fail fast on first error", 1),
                    ("2 Attempts", "Standard quick retry", 2),
                    ("3 Attempts", "Recommended default for self-repair", 3),
                    ("5 Attempts", "Maximum thorough repair effort", 5),
                    ("Back", "Cancel", "cancel")
                ]
                a_choice = select_menu_option("SELECT MAX REPAIR ATTEMPTS", att_opts)
                if a_choice and a_choice != "cancel":
                    self.config.repair.max_attempts = a_choice

    def _edit_approval(self) -> None:
        """Interactive settings for Approval Gates 1, 2, and 3."""
        while True:
            gate_opts = [
                (f"Gate 1 (Plan Approval): {'[green]ON[/green]' if self.config.approval.plan else '[dim]OFF[/dim]'}", "Require human approval before DAG worker execution", "toggle_plan"),
                (f"Gate 2 (Validation Approval): {'[green]ON[/green]' if self.config.approval.build else '[dim]OFF[/dim]'}", "Require human approval before packaging production build", "toggle_build"),
                (f"Gate 3 (Export Approval): {'[green]ON[/green]' if self.config.approval.export else '[dim]OFF[/dim]'}", "Require human approval before finalizing export in dist/", "toggle_export"),
                ("Back", "Return to Settings Menu", "back")
            ]
            choice = select_menu_option("APPROVAL GATES CONFIGURATION", gate_opts)
            if not choice or choice == "back":
                break
            elif choice == "toggle_plan":
                self.config.approval.plan = not self.config.approval.plan
            elif choice == "toggle_build":
                self.config.approval.build = not self.config.approval.build
            elif choice == "toggle_export":
                self.config.approval.export = not self.config.approval.export

    def _edit_security(self) -> None:
        """Interactive security thresholds."""
        while True:
            sec_opts = [
                (f"Critical Vulnerability Action: [bold red]{self.config.security.critical_failure.upper()}[/bold red]", "Action when critical security flaw is detected", "set_crit"),
                (f"High Vulnerability Action: [bold yellow]{self.config.security.high_failure.upper()}[/bold yellow]", "Action when high security flaw is detected", "set_high"),
                ("Back", "Return to Settings Menu", "back")
            ]
            choice = select_menu_option("SECURITY POLICIES & THRESHOLDS", sec_opts)
            if not choice or choice == "back":
                break
            elif choice == "set_crit":
                c_opts = [
                    ("1. Block Pipeline", "Halt factory build immediately until resolved", "block"),
                    ("2. Warn Only", "Log prominent alert but allow pipeline to proceed", "warn"),
                    ("3. Ignore", "Bypass critical security gate", "ignore"),
                    ("Back", "Cancel", "cancel")
                ]
                c_choice = select_menu_option("CRITICAL VULNERABILITY POLICY", c_opts)
                if c_choice and c_choice != "cancel":
                    self.config.security.critical_failure = c_choice
            elif choice == "set_high":
                h_opts = [
                    ("1. Block Pipeline", "Halt factory build immediately", "block"),
                    ("2. Warn Only", "Log prominent alert but proceed", "warn"),
                    ("3. Ignore", "Bypass high security gate", "ignore"),
                    ("Back", "Cancel", "cancel")
                ]
                h_choice = select_menu_option("HIGH VULNERABILITY POLICY", h_opts)
                if h_choice and h_choice != "cancel":
                    self.config.security.high_failure = h_choice

    def _edit_review(self) -> None:
        """Interactive review engine settings."""
        while True:
            rev_opts = [
                (f"Independent Review: {'[green]REQUIRED[/green]' if self.config.review.required else '[dim]OPTIONAL[/dim]'}", "Require 4-quadrant audit before release", "toggle_req"),
                (f"Auto-Revision on Findings: {'[green]ON[/green]' if self.config.review.auto_revision else '[dim]OFF[/dim]'}", "Automatically trigger repair loop on audit findings", "toggle_auto"),
                (f"Max Review-Repair Cycles: {self.config.review.max_repair_cycles}", "Maximum review-repair iterations allowed", "set_cycles"),
                ("Back", "Return to Settings Menu", "back")
            ]
            choice = select_menu_option("INDEPENDENT REVIEWER LOOP SETTINGS", rev_opts)
            if not choice or choice == "back":
                break
            elif choice == "toggle_req":
                self.config.review.required = not self.config.review.required
            elif choice == "toggle_auto":
                self.config.review.auto_revision = not self.config.review.auto_revision
            elif choice == "set_cycles":
                cyc_opts = [
                    ("1 Cycle", "Single audit pass, no automatic review-repair", 1),
                    ("2 Cycles", "Double audit-repair iteration", 2),
                    ("3 Cycles", "Recommended default for review-repair loop", 3),
                    ("5 Cycles", "Maximum thorough review-repair effort", 5),
                    ("Back", "Cancel", "cancel")
                ]
                c_choice = select_menu_option("SELECT MAX REVIEW CYCLES", cyc_opts)
                if c_choice and c_choice != "cancel":
                    self.config.review.max_repair_cycles = c_choice

    def _test_all_connections(self) -> None:
        """Perform comprehensive live ping and diagnostic checks on all AI providers."""
        self.console.print("\n[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]")
        self.console.print("[bold bright_cyan]  📡  LIVE AI PROVIDER CONNECTION DIAGNOSTICS[/bold bright_cyan]")
        self.console.print("[bold cyan]══════════════════════════════════════════════════════════════[/bold cyan]\n")

        table = Table(border_style="cyan", show_lines=True)
        table.add_column("Provider", style="bold white", width=22)
        table.add_column("Type", style="cyan", width=14)
        table.add_column("Live Status", width=18)
        table.add_column("Latency / Details", style="dim white")

        providers = self.detector.detect_providers()

        # 1. Test Codex
        codex_info = providers.get("codex", {})
        if codex_info.get("available"):
            table.add_row("Codex CLI", "CLI Tool", "[bold green]✓ Ready / Connected[/bold green]", codex_info.get("path") or "CLI binary in PATH")
        else:
            table.add_row("Codex CLI", "CLI Tool", "[dim red]✗ Not Detected[/dim red]", "Install via npm or set OPENAI_API_KEY")

        # 2. Test Antigravity / AGY
        agy_info = providers.get("agy", {})
        if agy_info.get("available"):
            table.add_row("Antigravity (AGY)", "CLI Tool", "[bold green]✓ Ready / Connected[/bold green]", agy_info.get("path") or "AGY binary detected")
        else:
            table.add_row("Antigravity (AGY)", "CLI Tool", "[dim red]✗ Not Detected[/dim red]", "Install Antigravity CLI or set GEMINI_API_KEY")

        # 3. Test Claude Code
        claude_info = providers.get("claude", {})
        if claude_info.get("available"):
            table.add_row("Claude Code CLI", "CLI Tool", "[bold green]✓ Ready / Connected[/bold green]", claude_info.get("path") or "Claude Code CLI detected")
        else:
            table.add_row("Claude Code CLI", "CLI Tool", "[dim red]✗ Not Detected[/dim red]", "Install claude-code or set ANTHROPIC_API_KEY")

        # 4. Test Ollama REST HTTP Server
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        t0 = time.time()
        try:
            req = urllib.request.Request(f"{ollama_host}/api/tags", headers={"User-Agent": "Dinggo/0.2.1"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    ollama_models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    latency = (time.time() - t0) * 1000.0
                    models_str = f"Latency: {latency:.1f}ms | Models: {', '.join(ollama_models[:3])}" + (f" (+{len(ollama_models)-3} more)" if len(ollama_models) > 3 else "")
                    table.add_row("Ollama Server", "Local REST API", "[bold green]✓ Online (200 OK)[/bold green]", models_str)
        except Exception:
            table.add_row("Ollama Server", "Local REST API", "[bold red]✗ Offline / Unreachable[/bold red]", f"{ollama_host} (Run 'ollama serve')")

        self.console.print(table)
        self.console.print()

        exit_opts = [("Back", "Return to Settings Menu", "back")]
        select_menu_option("DIAGNOSTIC COMPLETE", exit_opts)

    def save_config(self) -> None:
        """Save configuration to dinggo.yaml."""
        cfg_path = os.path.join(self.root_dir, "dinggo.yaml")
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.config.model_dump(mode="json"), f, sort_keys=False)
            self.console.print(f"[bold green]✓ Settings saved to {cfg_path}[/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]❌ Failed to save settings: {e}[/bold red]")
