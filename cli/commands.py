import os
import subprocess
from typing import Dict, Any, List


class SlashCommandHandler:
    """
    Handler for slash commands in Dinggo CLI (/help, /config, /models, /memory, /status, /clear, /compact).
    Inspired by Claude Code and Codex CLI.
    """

    def __init__(self, ui, ollama_client, project_context, short_term_memory, long_term_memory, contextix_adapter=None):
        self.ui = ui
        self.client = ollama_client
        self.context = project_context
        self.short_memory = short_term_memory
        self.long_memory = long_term_memory
        self.contextix_adapter = contextix_adapter

    def get_git_branch(self) -> str:
        """Gets current git branch name if inside git repository."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.context.working_dir,
                capture_output=True,
                text=True,
                timeout=2
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:
            pass
        return "Not a git repo"

    def handle_command(self, command_str: str) -> bool:
        """
        Executes slash command. Returns True if command was handled, False if unknown.
        """
        cmd = command_str.strip().lower()
        parts = cmd.split()
        main_cmd = parts[0]

        if main_cmd in ("/help", "/?", "help"):
            self.ui.render_help()
            return True

        elif main_cmd in ("/contextix", "/context", "contextix", "context"):
            if self.contextix_adapter:
                subcmd = parts[1] if len(parts) > 1 else "status"
                if subcmd in ("generate", "gen", "update", "run"):
                    self.ui.console.print("\n[bold cyan]🔄 Menjalankan 'contextix generate' untuk memperbarui memori proyek...[/bold cyan]")
                    res = self.contextix_adapter.run_generate()
                    if res["success"]:
                        self.ui.console.print(f"[bold green]✓ Contextix generate selesai dalam {res['elapsed']}s.[/bold green]")
                    else:
                        self.ui.console.print(f"[bold red]❌ Contextix generate gagal:[/bold red] {res.get('error')}")
                else:
                    self.ui.render_contextix_status(self.contextix_adapter.get_status())
            else:
                self.ui.console.print("[yellow]Modul ContextixAdapter belum diinisialisasi.[/yellow]")
            return True

        elif main_cmd in ("/config", "/settings", "config", "settings"):
            config_data = {
                "OLLAMA_BASE_URL": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "MODEL_INTENT_PARSER": os.getenv("MODEL_INTENT_PARSER", "gemma-sea-lion"),
                "MODEL_PLANNER": os.getenv("MODEL_PLANNER", "qwen3.5:4b"),
                "MODEL_CODEGEN": os.getenv("MODEL_CODEGEN", "qwen2.5:3b"),
                "FORCE_UNLOAD_BETWEEN_LAYERS": os.getenv("FORCE_UNLOAD_BETWEEN_LAYERS", "true"),
                "MAX_JSON_RETRY": os.getenv("MAX_JSON_RETRY", "3"),
                "OLLAMA_NUM_GPU": os.getenv("OLLAMA_NUM_GPU", "99"),
                "OLLAMA_NUM_THREAD": os.getenv("OLLAMA_NUM_THREAD", "4"),
            }
            self.ui.render_config(config_data)
            return True

        elif main_cmd in ("/models", "models"):
            installed = self.client.list_installed_models()
            active_models = {
                "Layer 1 (Intent)": os.getenv("MODEL_INTENT_PARSER", "gemma-sea-lion"),
                "Layer 2 (Planner)": os.getenv("MODEL_PLANNER", "qwen3.5:4b"),
                "Layer 3 (Codegen)": os.getenv("MODEL_CODEGEN", "qwen2.5:3b")
            }
            self.ui.render_models(installed, active_models)
            return True

        elif main_cmd in ("/memory", "memory"):
            self.ui.render_memory_status(
                context_info=self.context.get_info(),
                short_memory_str=self.short_memory.get_formatted_context(),
                graph_info_str=self.long_memory.get_formatted_graph_context()
            )
            return True

        elif main_cmd in ("/status", "status"):
            status_data = {
                "working_dir": self.context.working_dir,
                "git_branch": self.get_git_branch(),
                "ollama_online": self.client.is_available(),
                "ollama_url": self.client.base_url,
                "memory_turns": len(self.short_memory.history),
                "gpu_offload": os.getenv("OLLAMA_NUM_GPU", "99"),
                "cpu_threads": os.getenv("OLLAMA_NUM_THREAD", "4")
            }
            self.ui.render_status(status_data)
            return True

        elif main_cmd in ("/clear", "clear"):
            self.short_memory.clear()
            # Clear console screen
            os.system("cls" if os.name == "nt" else "clear")
            self.ui.render_banner(self.context.working_dir)
            self.ui.console.print("[bold yellow]🧹 Short-Term Memory & Terminal Screen telah dibersihkan.[/bold yellow]")
            return True

        elif main_cmd in ("/compact", "compact"):
            if len(self.short_memory.history) > 2:
                # Keep only latest turn and a summary
                latest = self.short_memory.history[-2:]
                self.short_memory.history = [
                    {
                        "prompt": "Compact Memory Summary",
                        "category": "TASK",
                        "summary": f"Ringkasan riwayat sebelumnya ({len(self.short_memory.history)-2} turn).",
                        "target_scope": [],
                        "execution_summary": "Riwayat percakapan sebelumnya disingkat."
                    }
                ] + latest
                self.short_memory.save()
                self.ui.console.print("[bold green]📦 Short-Term Memory berhasil diringkas (compacted).[/bold green]")
            else:
                self.ui.console.print("[dim]Riwayat percakapan masih pendek (tidak perlu ringkas).[/dim]")
            return True

        return False
