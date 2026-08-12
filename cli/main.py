import os
import sys
import time
from typing import Optional

from core.ollama_client import OllamaClient
from core.intent_parser import IntentParser
from core.planner import Planner
from core.executor import Executor
from cli.ui import TerminalUI


def main():
    """Main CLI entrypoint for Dinggo."""
    ui = TerminalUI()
    working_dir = os.getcwd()
    ui.render_banner(working_dir)

    ollama_client = OllamaClient()
    if not ollama_client.is_available():
        ui.console.print(
            "\n[bold red]❌ Gagal terhubung ke Ollama REST API![/bold red]\n"
            "[yellow]Pastikan Ollama sudah berjalan (misal: 'ollama serve') di http://localhost:11434[/yellow]"
        )
        sys.exit(1)

    intent_parser = IntentParser(ollama_client=ollama_client)
    planner = Planner(ollama_client=ollama_client)
    executor = Executor(
        ollama_client=ollama_client,
        confirm_command_callback=ui.confirm_shell_command
    )

    ui.console.print("[dim]Ketik 'exit' atau 'keluar' untuk mengakhiri sesi.[/dim]")

    while True:
        user_input = ui.get_user_prompt()
        if not user_input or user_input.lower() in ("exit", "keluar", "q"):
            ui.console.print("[bold cyan]Sampai jumpa! Dinggo CLI selesai.[/bold cyan]")
            break

        # Layer 1: Intent Parsing
        t_intent_start = time.time()
        ui.show_status("intent", "Mencerna maksud dan target instruksi...")
        intent_res = intent_parser.parse(user_input)
        t_intent_elapsed = time.time() - t_intent_start

        if not intent_res["success"]:
            ui.console.print(f"[bold red]❌ Intent Parsing Gagal (⏱️ {t_intent_elapsed:.2f}s):[/bold red] {intent_res['error']}")
            continue

        intent_data = intent_res["intent"]
        ui.render_intent(intent_data, elapsed=t_intent_elapsed)

        # Check if input is a task execution command vs casual chat/greeting
        is_task = intent_data.get("is_task", True)
        task_type = intent_data.get("task_type", "").lower()
        direct_resp = intent_data.get("direct_response")

        if not is_task or task_type in ("chat", "general_chat"):
            response_msg = direct_resp or intent_data.get("summary") or "Halo! Ada yang bisa saya bantu dengan proyek Anda hari ini?"
            ui.render_direct_response(response_msg, elapsed=t_intent_elapsed)
            continue

        # Layer 2: Planning Loop (supports revision)
        revision_feedback: Optional[str] = None
        plan_approved = False
        final_plan = None

        while not plan_approved:
            status_msg = "Menyusun alur kerja dan penentuan tools..." if not revision_feedback else "Memperbaiki plan sesuai revisi pengguna..."
            ui.show_status("planner", status_msg)

            t_plan_start = time.time()
            plan_res = planner.create_plan(
                intent_data=intent_data,
                revision_feedback=revision_feedback
            )
            t_plan_elapsed = time.time() - t_plan_start

            if not plan_res["success"]:
                ui.console.print(f"[bold red]❌ Planning Gagal (⏱️ {t_plan_elapsed:.2f}s):[/bold red] {plan_res['error']}")
                break

            final_plan = plan_res["plan"]
            ui.render_plan(final_plan, elapsed=t_plan_elapsed)

            choice, rev_text = ui.prompt_confirm_plan()
            if choice == "Y":
                plan_approved = True
            elif choice == "N":
                ui.console.print("[bold yellow]Plan dibatalkan oleh pengguna.[/bold yellow]")
                break
            elif choice == "R":
                revision_feedback = rev_text

        if not plan_approved or not final_plan:
            continue

        # Layer 3: Executor
        t_exec_start = time.time()
        ui.show_status("executor", "Mulai mengeksekusi langkah-langkah...")
        steps = final_plan.get("steps", [])

        completed_count = 0
        for step in steps:
            step_num = step.get("step_number", 0)
            action = step.get("action_type", "")
            desc = step.get("description", "")

            if action in ("write_file", "edit_file", "generate_code"):
                ui.show_status("codegen", f"Menulis kode Python untuk step {step_num}: {desc}")
            else:
                ui.show_status("executor", f"Menjalankan tool {action} ({desc})")

            t_step_start = time.time()
            res = executor.execute_step(step, project_root=working_dir)
            t_step_elapsed = time.time() - t_step_start

            ui.render_step_result(step_num, action, res, elapsed=t_step_elapsed)

            if res["success"]:
                completed_count += 1
            else:
                ui.console.print(f"[bold red]Proses terhenti di step {step_num} karena terjadi kesalahan.[/bold red]")
                break

        t_exec_total = time.time() - t_exec_start
        ui.console.print(f"\n[bold green]✨ Selesai: {completed_count}/{len(steps)} langkah telah dieksekusi.[/bold green] [dim cyan](⏱️ Total Eksekusi: {t_exec_total:.2f}s)[/dim cyan]")


if __name__ == "__main__":
    main()
