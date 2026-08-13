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
from prompt_toolkit.completion import Completer, Completion


class SlashCompleter(Completer):
    """
    Custom completer that ONLY triggers when the input prompt line starts with '/'.
    Prevents annoying autocomplete popups when typing regular prompts/instructions.
    """
    def __init__(self, commands: List[str]):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        if text_before.startswith("/"):
            for cmd in self.commands:
                if cmd.lower().startswith(text_before.lower()):
                    yield Completion(cmd, start_position=-len(text_before))


class TerminalUI:
    """
    Terminal UI Renderer using Rich and PromptToolkit.
    Enforces design specifications from docs/08-design.md with live updating timer badges and slash commands UI.
    """

    def __init__(self):
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass
        self.console = Console()
        history_path = os.path.expanduser("~/.dinggo_history")
        slash_commands = ["/help", "/config", "/models", "/memory", "/contextix", "/status", "/clear", "/compact", "/exit"]
        completer = SlashCompleter(slash_commands)
        try:
            self.session = PromptSession(history=FileHistory(history_path), completer=completer)
        except Exception:
            self.session = None

    def render_banner(self, working_dir: str):
        """Displays futuristic ASCII logo banner & active working directory."""
        logo_text = (
            "[bold cyan]  ___  ___ _  _ ___ ___  ___   [/bold cyan]\n"
            "[bold bright_cyan] |   \\|_ _| \\| / __/ __|/ _ \\  [/bold bright_cyan]\n"
            "[bold bright_blue] | |) | || .` | (_| (_ | (_) | [/bold bright_blue]\n"
            "[bold blue] |___/___|_|\\_|\\___\\___|\\___/  [/bold blue]"
        )
        subtitle = (
            f"[bold white]🐕 DINGGO CLI IDE[/bold white] [dim]v0.1.0 — Local 3-Layer AI Orchestrator[/dim]\n"
            f"[bold yellow]📍 Workspace Root:[/bold yellow] [bold green]{working_dir}[/bold green]\n"
            f"[bold cyan]🤖 Orchestration:[/bold cyan] [blue]Gemma-SEA-LION (L1)[/blue] ➔ [magenta]Qwen3.5-4B (L2)[/magenta] ➔ [yellow]Qwen2.5-Coder (L3)[/yellow]"
        )
        
        banner_panel = Panel(
            Text.from_markup(f"{logo_text}\n\n{subtitle}"),
            border_style="bright_cyan",
            expand=False,
            padding=(1, 2)
        )
        self.console.print(banner_panel)

    @contextmanager
    def live_status(self, layer: str, message: str) -> Generator[Dict[str, float], None, None]:
        """
        Context manager providing a live updating status spinner with real-time timer ticker (ticks every 100ms).
        """
        badges = {
            "intent": "[bold white on blue] 🗣️  L1 INTENT [/bold white on blue] [bold cyan]Nyimak...[/bold cyan]",
            "planner": "[bold white on magenta] 🧠 L2 PLANNER [/bold white on magenta] [bold magenta]Mikir plan...[/bold magenta]",
            "codegen": "[bold black on yellow] ⚡ L3 CODEGEN [/bold black on yellow] [bold yellow]Nulis kode...[/bold yellow]",
            "executor": "[bold white on green] 🔧 L3 EXECUTOR [/bold white on green] [bold green]Ngerjain tool:[/bold green]",
            "validator": "[bold black on cyan] 🔍 L4 VALIDATOR [/bold black on cyan] [bold cyan]Validasi semantik...[/bold cyan]"
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
            "intent": ("[bold white on blue] 🗣️  L1 INTENT [/bold white on blue]", "cyan"),
            "planner": ("[bold white on magenta] 🧠 L2 PLANNER [/bold white on magenta]", "magenta"),
            "codegen": ("[bold black on yellow] ⚡ L3 CODEGEN [/bold black on yellow]", "yellow"),
            "executor": ("[bold white on green] 🔧 L3 EXECUTOR [/bold white on green]", "green")
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
            "TASK": "[bold black on yellow] ⚡ TASK [/bold black on yellow]",
            "CONVERSATION": "[bold white on cyan] 💬 CONVERSATION [/bold white on cyan]",
            "CLARIFICATION": "[bold white on magenta] ❓ CLARIFICATION [/bold white on magenta]"
        }
        cat_badge = cat_styles.get(category, f"[bold white]{category}[/bold white]")

        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Key", style="bold cyan", width=14)
        table.add_column("Value")

        table.add_row("Kategori", cat_badge)
        table.add_row("Tipe Task", f"[bold yellow]{task_type}[/bold yellow]")
        table.add_row("Maksud/Intent", f"[white]{summary}[/white]")
        table.add_row("Target Scope", f"[green]{scope}[/green]")

        timer_str = f" [dim cyan](⏱️ {elapsed:.2f}s)[/dim cyan]" if elapsed is not None else ""
        self.console.print(Panel(
            table,
            title=f"[bold blue]🗣️ Layer 1: Structured Intent[/bold blue]{timer_str}",
            border_style="blue",
            padding=(0, 1)
        ))

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
        table.add_column("Step", style="dim cyan", width=6, justify="center")
        table.add_column("Aksi / Tool", style="bold yellow", width=15)
        table.add_column("Detail Langkah Pengerjaan", style="white")
        table.add_column("Target Path / Command", style="bold green")

        for step in steps:
            no = f"#{step.get('step_number', '')}"
            action = step.get("action_type", "")
            desc = step.get("description", "")
            target = step.get("target_path") or step.get("command") or "-"
            table.add_row(no, action, desc, target)

        timer_str = f" [dim magenta](⏱️ {elapsed:.2f}s)[/dim magenta]" if elapsed is not None else ""
        panel = Panel(
            table,
            title=f"[bold magenta]🧠 Layer 2: Execution Plan — {summary}[/bold magenta]{timer_str}",
            border_style="magenta",
            expand=False,
            padding=(1, 2)
        )
        self.console.print("\n", panel)

    def prompt_confirm_plan(self) -> Tuple[str, str]:
        """
        Prompts user to confirm, cancel, or revise the plan.
        Returns ('Y'|'N'|'R', revision_text)
        """
        self.console.print("\n[bold yellow]⚡ KONFIRMASI EKSKUSI PLAN:[/bold yellow]  [bold green][Y] ✅ Lanjut[/bold green]  │  [bold red][N] ❌ Batal[/bold red]  │  [bold magenta][R] 📝 Revisi Plan[/bold magenta]")
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
        self.console.print("\n[bold red]⚠️ PERINGATAN KEAMANAN EKSEKUSI SHELL COMMAND[/bold red]")
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

    def render_code_preview(self, file_path: str, code_content: str, max_lines: int = 20):
        """Renders syntax-highlighted preview of newly written code/document."""
        if not code_content or not code_content.strip():
            return
        lines = code_content.splitlines()
        preview_lines = lines[:max_lines]
        preview_text = "\n".join(preview_lines)
        if len(lines) > max_lines:
            preview_text += f"\n... ({len(lines) - max_lines} baris lainnya)"

        ext = os.path.splitext(file_path)[1].lower().strip(".")
        lexer_name = ext if ext in ("py", "json", "yaml", "yml", "md", "html", "css", "sh", "txt") else "text"
        syntax = Syntax(preview_text, lexer_name, theme="monokai", line_numbers=True)
        self.console.print(Panel(
            syntax,
            title=f"[bold cyan]Pratinjau Kode: {file_path}[/bold cyan]",
            border_style="cyan"
        ))

    def render_step_result(self, step_num: int, action: str, result: Dict[str, Any], elapsed: Optional[float] = None):
        """Displays step completion checklist icon, output/error, and execution timer."""
        timer_str = f" [dim green](⏱️ {elapsed:.2f}s)[/dim green]" if elapsed is not None else ""
        if result["success"]:
            self.console.print(f"[bold green]  ✓ Step {step_num} [{action}]: Selesai[/bold green]{timer_str}")
            target_path = result.get("target_path", "file")
            if result.get("diff"):
                self.render_diff(target_path, result["diff"])
            elif result.get("code_content"):
                self.render_code_preview(target_path, result["code_content"])
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

    def render_missing_models_warning(self, missing_models: List[str]):
        """Displays friendly warning box for missing local Ollama models."""
        table = Table(show_header=True, header_style="bold yellow", box=None, expand=True)
        table.add_column("Model Dikonfigurasi", style="bold red", width=25)
        table.add_column("Perintah Instalasi (Jalankan di Terminal)", style="bold green")

        for m in missing_models:
            table.add_row(m, f"ollama pull {m}")

        self.console.print(Panel(
            table,
            title="[bold yellow]⚠️ Perhatian: Beberapa Model Ollama Belum Terdeteksi[/bold yellow]",
            border_style="yellow",
            subtitle="[dim]Jalankan perintah 'ollama pull' di atas agar model dapat digunakan[/dim]"
        ))

    def render_memory_status(self, context_info: Dict[str, Any], short_memory_str: str, graph_info_str: str):
        """Displays project memory details and storage location."""
        info_text = (
            f"[bold yellow]Proyek:[/bold yellow] [green]{context_info.get('project_name')}[/green] ({context_info.get('project_hash')})\n"
            f"[bold yellow]Lokasi Simpanan Memori Global:[/bold yellow] [dim]{context_info.get('storage_dir')}[/dim]\n\n"
            f"[bold cyan]🧠 Short-Term Memory (Riwayat Percakapan Terakhir):[/bold cyan]\n"
            f"{short_memory_str}\n\n"
            f"[bold magenta]🕸️ Long-Term Memory (Code Knowledge Graph & Embeddings):[/bold magenta]\n"
            f"{graph_info_str}"
        )
        self.console.print(Panel(
            Text.from_markup(info_text),
            title="[bold green]🧠 Dinggo Memory System Status[/bold green]",
            border_style="green"
        ))

    def render_contextix_status(self, ctx_status: Dict[str, Any]):
        """Displays Contextix project memory integration dashboard."""
        avail_str = "[bold green]ONLINE ✅[/bold green]" if ctx_status.get("available") else "[bold red]NOT INSTALLED ❌[/bold red]"
        ctx_str = "[bold green]TERBENTUK ✅[/bold green]" if ctx_status.get("has_context") else "[bold yellow]BELUM ADA ⚠️[/bold yellow]"

        info_text = (
            f"[bold yellow]Contextix CLI Status:[/bold yellow] {avail_str}\n"
            f"[bold yellow]Status Memori .context/:[/bold yellow] {ctx_str} ([dim]{ctx_status.get('context_dir')}[/dim])\n"
            f"[bold yellow]Nama Proyek (Contextix):[/bold yellow] [green]{ctx_status.get('project_name')}[/green]\n"
            f"[bold yellow]Keputusan Terdaftar (Decisions):[/bold yellow] [cyan]{ctx_status.get('decisions_count')} keputusan[/cyan]\n"
            f"[bold yellow]Batasan Proyek (Constraints):[/bold yellow] [magenta]{ctx_status.get('constraints_count')} hard rules[/magenta]\n"
            f"[bold yellow]File Bootstrap / YAML:[/bold yellow] [white]bootstrap.md ({'✅' if ctx_status.get('bootstrap_exists') else '❌'}) | context.yaml ({'✅' if ctx_status.get('yaml_exists') else '❌'})[/white]\n\n"
            f"[dim cyan]💡 Tip: Ketik '/contextix generate' untuk memperbarui memori snapshot proyek.[/dim cyan]"
        )
        self.console.print(Panel(
            Text.from_markup(info_text),
            title="[bold cyan]📦 Contextix Memory Integration Status[/bold cyan]",
            border_style="cyan"
        ))

    def render_help(self):
        """Displays interactive Slash Commands & Settings Help Menu."""
        table = Table(show_header=True, header_style="bold cyan", box=None, expand=True)
        table.add_column("Perintah / Slash Command", style="bold yellow", width=22)
        table.add_column("Keterangan & Fungsi", style="white")

        table.add_row("/help, /?", "Menampilkan daftar perintah slash & bantuan ini")
        table.add_row("/config, /settings", "Melihat & mengonfigurasi pengaturan aktif (Model, Temp, GPU, Thread)")
        table.add_row("/models", "Daftar model Ollama lokal & pemetaan layer aktif")
        table.add_row("/memory", "Melihat status memori proyek (Short-term & Code Graph)")
        table.add_row("/contextix, /context", "Status & manajemen memori Contextix (.context/ generate/status)")
        table.add_row("/status", "Melihat status lingkungan (Git branch, Ollama, GPU offload)")
        table.add_row("/clear", "Membersihkan riwayat percakapan short-term & layar terminal")
        table.add_row("/compact", "Meringkas (compact) riwayat memori percakapan")
        table.add_row("/exit, exit, keluar", "Keluar dari sesi Dinggo CLI IDE")

        self.console.print(Panel(
            table,
            title="[bold cyan]💡 Menu Perintah & Slash Commands Dinggo CLI[/bold cyan]",
            border_style="cyan"
        ))

    def render_config(self, config_dict: Dict[str, Any]):
        """Displays active configuration table."""
        table = Table(show_header=True, header_style="bold yellow", box=None, expand=True)
        table.add_column("Parameter Konfigurasi", style="bold cyan", width=30)
        table.add_column("Nilai Aktif", style="bold green")

        for key, val in config_dict.items():
            table.add_row(key, str(val))

        self.console.print(Panel(
            table,
            title="[bold yellow]⚙️ Pengaturan & Konfigurasi Aktif (.env)[/bold yellow]",
            border_style="yellow"
        ))

    def render_models(self, installed_models: List[str], active_models: Dict[str, str]):
        """Displays installed Ollama models and active layer assignments."""
        table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
        table.add_column("Layer Orchestration", style="bold yellow", width=22)
        table.add_column("Model Aktif Termanfaatkan", style="bold cyan")

        for layer, model in active_models.items():
            table.add_row(layer, model)

        installed_str = ", ".join([f"[green]{m}[/green]" for m in installed_models]) if installed_models else "[red]Tidak ada model terdeteksi[/red]"
        
        self.console.print(Panel(
            table,
            title="[bold magenta]🤖 Status Model LLM & Alokasi Layer[/bold magenta]",
            border_style="magenta",
            subtitle=f"[dim]Total {len(installed_models)} Model Tersedia[/dim]"
        ))

    def render_status(self, status_dict: Dict[str, Any]):
        """Displays environment & system status dashboard."""
        status_text = (
            f"[bold yellow]Direktori Kerja (Root):[/bold yellow] [green]{status_dict.get('working_dir')}[/green]\n"
            f"[bold yellow]Git Branch:[/bold yellow] [cyan]{status_dict.get('git_branch')}[/cyan]\n"
            f"[bold yellow]Ollama Service Status:[/bold yellow] [{'green' if status_dict.get('ollama_online') else 'red'}]{'ONLINE ✅' if status_dict.get('ollama_online') else 'OFFLINE ❌'}[/{'green' if status_dict.get('ollama_online') else 'red'}] ({status_dict.get('ollama_url')})\n"
            f"[bold yellow]GPU Offload Layers:[/bold yellow] [magenta]num_gpu = {status_dict.get('gpu_offload')}[/magenta]\n"
            f"[bold yellow]CPU Thread Limit:[/bold yellow] [magenta]num_thread = {status_dict.get('cpu_threads')}[/magenta]\n"
            f"[bold yellow]Riwayat Short-Term Memory:[/bold yellow] [cyan]{status_dict.get('memory_turns')} turn terdaftar[/cyan]"
        )
        self.console.print(Panel(
            Text.from_markup(status_text),
            title="[bold green]📊 Dinggo CLI Environment Status[/bold green]",
            border_style="green"
        ))

    def get_user_prompt(self) -> str:
        """Gets user prompt input using prompt_toolkit with history and slash command completion."""
        try:
            if self.session:
                from prompt_toolkit.formatted_text import HTML
                return self.session.prompt(HTML('<cyan><b>🐕 dinggo</b></cyan> <brightblue><b>›</b></brightblue> ')).strip()
            return input("🐕 dinggo › ").strip()
        except (KeyboardInterrupt, EOFError):
            return "exit"
