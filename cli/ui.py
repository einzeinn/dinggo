import os
import sys
import time
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional, Tuple, List, Generator

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich.table import Table
from rich.prompt import Prompt
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


class TerminalUI:
    """
    Terminal UI Renderer using Rich and PromptToolkit.
    Enforces design specifications from docs/08-design.md with live updating timer badges.
    """

    def __init__(self):
        self.console = Console()
        history_path = os.path.expanduser("~/.dinggo_history")
        self.session = PromptSession(history=FileHistory(history_path))

    def render_banner(self, working_dir: str):
        """Displays ASCII logo banner & active working directory."""
        logo_text = (
            "[bold cyan]  ____  _   _  ____  ____  ___  [/bold cyan]\n"
            "[bold cyan] /  _ \\/ \\ / \\/  _ \\/  _ \\/  _ \\ [/bold cyan]\n"
            "[bold cyan] | | \\|| | | || | \\|| | \\|| / \\| [/bold cyan]\n"
            "[bold cyan] | |_/|| | | || |_/|| |_/|| \\_/| [/bold cyan]\n"
            "[bold cyan] \\____/\\_/ \\_/\\____/\\____/\\____/ [/bold cyan]"
        )
        subtitle = f"[dim]Dinggo CLI IDE v0.1.0 — Local AI Orchestrator[/dim]\n[bold yellow]Root:[/bold yellow] [green]{working_dir}[/green]"
        
        banner_panel = Panel(
            Text.from_markup(f"{logo_text}\n\n{subtitle}"),
            border_style="cyan",
            expand=False
        )
        self.console.print(banner_panel)

    @contextmanager
    def live_status(self, layer: str, message: str) -> Generator[Dict[str, float], None, None]:
        """
        Context manager providing a live updating status spinner with real-time timer ticker (ticks every 100ms).
        """
        badges = {
            "intent": "[bold blue]🗣️  Nyimak...[/bold blue]",
            "planner": "[bold magenta]🧠  Mikir dulu...[/bold magenta]",
            "codegen": "[bold yellow]⚡  Nulis kode...[/bold yellow]",
            "executor": "[bold green]🔧  Ngerjain:[/bold green]"
        }
        badge = badges.get(layer.lower(), "ℹ️ ")
        start_time = time.time()
        stop_event = threading.Event()
        timer_info = {"elapsed": 0.0}

        initial_text = f"\n{badge} [italic]{message}[/italic] [bold cyan](⏱️ 0.0s)[/bold cyan]"
        status = self.console.status(initial_text, spinner="dots")

        def tick():
            while not stop_event.is_set():
                elapsed = round(time.time() - start_time, 1)
                timer_info["elapsed"] = elapsed
                updated_text = f"\n{badge} [italic]{message}[/italic] [bold cyan](⏱️ {elapsed:.1f}s)[/bold cyan]"
                status.update(updated_text)
                time.sleep(0.1)

        status.start()
        thread = threading.Thread(target=tick, daemon=True)
        thread.start()

        try:
            yield timer_info
        finally:
            stop_event.set()
            thread.join(timeout=0.3)
            status.stop()
            timer_info["elapsed"] = round(time.time() - start_time, 2)

    def show_status(self, layer: str, message: str):
        """Displays static layer status badge."""
        badges = {
            "intent": ("[bold blue]🗣️  Nyimak...[/bold blue]", "cyan"),
            "planner": ("[bold magenta]🧠  Mikir dulu...[/bold magenta]", "magenta"),
            "codegen": ("[bold yellow]⚡  Nulis kode...[/bold yellow]", "yellow"),
            "executor": ("[bold green]🔧  Ngerjain:[/bold green]", "green")
        }
        badge, color = badges.get(layer.lower(), ("ℹ️ ", "white"))
        self.console.print(f"\n{badge} [italic]{message}[/italic]")

    def render_intent(self, intent_data: Dict[str, Any], elapsed: Optional[float] = None):
        """Displays structured intent parse summary with optional timer and category badge."""
        summary = intent_data.get("summary", "")
        category = intent_data.get("category", "TASK").upper()
        task_type = intent_data.get("task_type", "")
        scope = ", ".join(intent_data.get("target_scope", [])) or "Semua project"

        cat_styles = {
            "TASK": "[bold yellow]TASK[/bold yellow]",
            "CONVERSATION": "[bold cyan]CONVERSATION[/bold cyan]",
            "CLARIFICATION": "[bold magenta]CLARIFICATION[/bold magenta]"
        }
        cat_badge = cat_styles.get(category, f"[bold white]{category}[/bold white]")

        text = (
            f"[bold]Kategori:[/bold] {cat_badge}\n"
            f"[bold]Maksud:[/bold] {summary}\n"
            f"[bold]Tipe Task:[/bold] [cyan]{task_type}[/cyan]\n"
            f"[bold]Target Scope:[/bold] [yellow]{scope}[/yellow]"
        )
        timer_str = f" [dim cyan](⏱️ {elapsed:.2f}s)[/dim cyan]" if elapsed is not None else ""
        self.console.print(Panel(Text.from_markup(text), title=f"[bold blue]Structured Intent[/bold blue]{timer_str}", border_style="blue"))

    def render_direct_response(self, message: str, elapsed: Optional[float] = None):
        """Displays direct casual response for non-task inputs with timer."""
        timer_str = f" [dim cyan](⏱️ {elapsed:.2f}s)[/dim cyan]" if elapsed is not None else ""
        self.console.print(Panel(
            Text(message, style="bold cyan"),
            title=f"[bold cyan]💬 Response[/bold cyan]{timer_str}",
            border_style="cyan"
        ))

    def render_clarification(self, message: str, elapsed: Optional[float] = None):
        """Displays clarification request panel when user prompt is ambiguous."""
        timer_str = f" [dim magenta](⏱️ {elapsed:.2f}s)[/dim magenta]" if elapsed is not None else ""
        self.console.print(Panel(
            Text(message, style="bold yellow"),
            title=f"[bold yellow]❓ Clarification Required[/bold yellow]{timer_str}",
            border_style="yellow"
        ))

    def render_plan(self, plan_data: Dict[str, Any], elapsed: Optional[float] = None):
        """Displays numbered plan steps in a styled panel with optional timer."""
        summary = plan_data.get("intent_summary", "Rencana Eksekusi")
        steps = plan_data.get("steps", [])

        table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
        table.add_column("No.", style="dim", width=4)
        table.add_column("Aksi", style="cyan", width=14)
        table.add_column("Detail Langkah", style="white")
        table.add_column("Target / Command", style="yellow")

        for step in steps:
            no = str(step.get("step_number", ""))
            action = step.get("action_type", "")
            desc = step.get("description", "")
            target = step.get("target_path") or step.get("command") or "-"
            table.add_row(no, action, desc, target)

        timer_str = f" [dim magenta](⏱️ {elapsed:.2f}s)[/dim magenta]" if elapsed is not None else ""
        panel = Panel(
            table,
            title=f"[bold magenta]📋 Plan: {summary}[/bold magenta]{timer_str}",
            border_style="magenta",
            expand=False
        )
        self.console.print("\n", panel)

    def prompt_confirm_plan(self) -> Tuple[str, str]:
        """
        Prompts user to confirm, cancel, or revise the plan.
        Returns ('Y'|'N'|'R', revision_text)
        """
        self.console.print("\n[bold yellow][Y] Lanjut    [N] Batal    [R] Revisi Plan[/bold yellow]")
        while True:
            try:
                choice = Prompt.ask("[bold cyan]Pilihan Anda[/bold cyan]", choices=["y", "n", "r", "Y", "N", "R"], default="y").lower()
                if choice == "y":
                    return "Y", ""
                elif choice == "n":
                    return "N", ""
                elif choice == "r":
                    revision = Prompt.ask("[bold yellow]Masukkan masukan/revisi Anda[/bold yellow]")
                    return "R", revision
            except (KeyboardInterrupt, EOFError):
                return "N", ""

    def confirm_shell_command(self, command: str) -> bool:
        """
        Mandatory safety confirmation dialog before running shell commands.
        """
        self.console.print("\n[bold red]⚠️  PERINGATAN KEAMANAN EKSEKUSI SHELL COMMAND[/bold red]")
        self.console.print(Panel(
            Text.from_markup(f"[bold white]{command}[/bold white]"),
            title="[bold yellow]Command yang akan dijalankan[/bold yellow]",
            border_style="red"
        ))
        try:
            choice = Prompt.ask("[bold red]Apakah Anda mengizinkan eksekusi command ini?[/bold red]", choices=["y", "n"], default="n").lower()
            return choice == "y"
        except (KeyboardInterrupt, EOFError):
            return False

    def render_diff(self, file_path: str, diff_text: str):
        """Renders colorized unified diff for modified files."""
        if not diff_text.strip():
            self.console.print(f"[dim]Tidak ada perubahan karakter di {file_path}[/dim]")
            return

        syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=False)
        self.console.print(Panel(
            syntax,
            title=f"[bold green]Diff: {file_path}[/bold green]",
            border_style="green"
        ))

    def render_step_result(self, step_num: int, action: str, result: Dict[str, Any], elapsed: Optional[float] = None):
        """Displays step completion checklist icon, output/error, and execution timer."""
        timer_str = f" [dim green](⏱️ {elapsed:.2f}s)[/dim green]" if elapsed is not None else ""
        if result["success"]:
            self.console.print(f"[bold green]  ✓ Step {step_num} [{action}]: Selesai[/bold green]{timer_str}")
            if result.get("diff"):
                self.render_diff(result.get("target_path", "file"), result["diff"])
            elif result.get("output") and len(result["output"]) < 300:
                self.console.print(f"    [dim]{result['output']}[/dim]")
        else:
            self.console.print(f"[bold red]  ✗ Step {step_num} [{action}]: Gagal[/bold red]{timer_str}")
            err_msg = result.get("error") or result.get("output") or "Error tidak diketahui"
            self.console.print(Panel(
                Text(err_msg, style="bold red"),
                title=f"[bold red]Error Step {step_num}[/bold red]",
                border_style="red"
            ))

    def get_user_prompt(self) -> str:
        """Gets user prompt input using prompt_toolkit with history."""
        try:
            return self.session.prompt("\ndinggo > ").strip()
        except (KeyboardInterrupt, EOFError):
            return "exit"
