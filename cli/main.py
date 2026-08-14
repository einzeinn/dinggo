import os
import sys
import time
from typing import Optional

from core.ollama_client import OllamaClient
from core.intent_parser import IntentParser
from core.planner import Planner
from core.executor import Executor
from core.memory import ProjectContext, ShortTermMemory, LongTermMemory, ContextixAdapter
from cli.ui import TerminalUI
from cli.commands import SlashCommandHandler


def main():
    """Main CLI entrypoint for Dinggo."""
    ui = TerminalUI()
    working_dir = os.getcwd()
    ui.render_banner(os.path.basename(working_dir))

    ollama_client = OllamaClient()
    if not ollama_client.is_available():
        ui.console.print(
            "\n[bold red]❌ Gagal terhubung ke Ollama REST API![/bold red]\n"
            "[yellow]Pastikan Ollama sudah berjalan (misal: 'ollama serve') di http://localhost:11434[/yellow]"
        )
        sys.exit(1)

    # Initialize Memory System (Global Storage under ~/.dinggo/memory/<project>)
    project_context = ProjectContext(working_dir)
    short_term_memory = ShortTermMemory(project_context)
    long_term_memory = LongTermMemory(project_context, ollama_client)
    contextix_adapter = ContextixAdapter(project_context)
    
    # Build Code Knowledge Graph for current workspace
    long_term_memory.build_code_graph()

    # Ensure Contextix memory on startup (auto-generate if missing & CLI available)
    contextix_adapter.ensure_context_on_startup(ui)

    # Initialize Slash Command Handler
    cmd_handler = SlashCommandHandler(
        ui=ui,
        ollama_client=ollama_client,
        project_context=project_context,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        contextix_adapter=contextix_adapter
    )

    intent_parser = IntentParser(ollama_client=ollama_client)
    planner = Planner(ollama_client=ollama_client)
    executor = Executor(
        ollama_client=ollama_client,
        confirm_command_callback=ui.confirm_shell_command
    )

    # Perform startup health check for required local Ollama models
    installed_models = ollama_client.list_installed_models()
    required_models = [intent_parser.model_name, planner.model_name, executor.codegen_delegate.model_name]
    missing_models = []
    if installed_models:
        for rm in required_models:
            resolved = ollama_client.resolve_model_name(rm)
            if resolved not in installed_models and rm not in installed_models:
                if rm not in missing_models:
                    missing_models.append(rm)
    if missing_models:
        ui.render_missing_models_warning(missing_models)

    ui.console.print("[dim]Ketik '/help' untuk melihat perintah slash, atau 'exit' untuk mengakhiri sesi.[/dim]")

    while True:
        try:
            user_input = ui.get_user_prompt()
            if not user_input or user_input.lower() in ("exit", "keluar", "q"):
                ui.console.print("[bold cyan]Sampai jumpa! Dinggo CLI selesai.[/bold cyan]")
                break

            # Handle Slash Commands (/help, /config, /models, /status, /memory, /clear, /compact)
            if user_input.startswith("/") or user_input.lower() in ("help", "config", "models", "status", "memory", "clear", "compact"):
                if cmd_handler.handle_command(user_input):
                    continue

            # Get active short-term conversation context
            short_term_ctx = short_term_memory.get_formatted_context()

            # Pre-LLM fast-path: catch obvious greetings/chat patterns instantly (skip 15s+ LLM call)
            _lowered = user_input.strip().lower().rstrip("!?.,:;")
            _GREETING_PATTERNS = {
                "hi", "halo", "hai", "hello", "hey", "yo", "ping", "pong",
                "hei", "oi", "sup", "woi", "woy", "hola", "howdy",
                "selamat pagi", "selamat siang", "selamat sore", "selamat malam",
                "good morning", "good afternoon", "good evening", "good night",
                "makasih", "terima kasih", "thanks", "thank you", "thx",
                "apa kabar", "how are you", "what's up", "whats up",
            }
            if _lowered in _GREETING_PATTERNS or len(_lowered) <= 3 and not _lowered.startswith("/"):
                response_msg = "Hello! 🐕 How can I help you with your project today?"
                ui.render_direct_response(response_msg, elapsed=0.0)
                short_term_memory.add_turn(
                    prompt=user_input, category="CONVERSATION",
                    summary="User greeting", target_scope=[],
                    direct_response=response_msg
                )
                continue

            # Layer 1: Intent Parsing with live updating status timer & memory
            with ui.live_status("intent", "Parsing intent and target instruction...") as timer_intent:
                intent_res = intent_parser.parse(user_input, short_term_context=short_term_ctx)
            t_intent_elapsed = timer_intent["elapsed"]

            if not intent_res["success"]:
                ui.console.print(f"[bold red]❌ Intent Parsing Failed (⏱️ {t_intent_elapsed:.2f}s):[/bold red] {intent_res['error']}")
                continue

            intent_data = intent_res["intent"]
            ui.render_intent(intent_data, elapsed=t_intent_elapsed)

            # Category Routing: TASK | CONVERSATION | CLARIFICATION
            category = intent_data.get("category", "TASK").upper()
            is_task = intent_data.get("is_task", True)
            task_type = intent_data.get("task_type", "").lower()
            direct_resp = intent_data.get("direct_response")
            summary = intent_data.get("summary", "")
            target_scope = intent_data.get("target_scope", [])
            user_language = intent_data.get("user_language", "id")

            # 1. CONVERSATION
            if category == "CONVERSATION" or (not is_task and category not in ("CLARIFICATION", "TASK")):
                response_msg = direct_resp or summary or "Hello! How can I assist you with your project today?"
                ui.render_direct_response(response_msg, elapsed=t_intent_elapsed)
                short_term_memory.add_turn(
                    prompt=user_input,
                    category="CONVERSATION",
                    summary=summary,
                    target_scope=target_scope,
                    direct_response=response_msg
                )
                continue

            # 2. CLARIFICATION
            if category == "CLARIFICATION" or task_type == "clarification":
                clarification_msg = direct_resp or summary or "Could you please provide more specific details about the task you want to perform?"
                ui.render_clarification(clarification_msg, elapsed=t_intent_elapsed)
                short_term_memory.add_turn(
                    prompt=user_input,
                    category="CLARIFICATION",
                    summary=summary,
                    target_scope=target_scope,
                    direct_response=clarification_msg
                )
                continue

            # 3. QUESTION
            _is_question = (
                not is_task
                and category in ("QUESTION", "CONVERSATION")
            )
            if _is_question:
                long_term_ctx = long_term_memory.get_formatted_graph_context(target_scope=target_scope)
                contextix_ctx = contextix_adapter.get_relevant_context(target_scope=target_scope, summary=summary)
                ctx_block = f"{contextix_ctx}\n\n{long_term_ctx}".strip()

                q_system = (
                    "You are the Dinggo project assistant. Answer the user's question based on the provided project context.\n"
                    "Respond in the same language as the user's prompt. Be friendly, concise, informative, and direct.\n"
                    "DO NOT write internal reasoning or 'Thinking Process'."
                )
                q_prompt = f"[Project Context]\n{ctx_block}\n\n[User Question]\n{user_input}"

                with ui.live_status("planner", "Analyzing project context...") as timer_q:
                    q_res = ollama_client.generate(
                        model=planner.model_name,
                        prompt=q_prompt,
                        system_prompt=q_system,
                        json_format=False,
                        think=False,
                        temperature=0.2,
                        num_ctx=4096,
                        num_predict=512
                    )
                t_q_elapsed = timer_q["elapsed"]

                if q_res.get("success"):
                    import re as _re
                    raw_ans = q_res["response"]
                    ans = _re.sub(r"<think>[\s\S]*?</think>", "", raw_ans, flags=_re.IGNORECASE).strip()
                    ans = _re.sub(r"(?:Thinking Process|Proses Berpikir|Reasoning):[\s\S]*?(?=\n\n[A-Z0-9#\*]|\Z)", "", ans, flags=_re.IGNORECASE).strip()
                    answer = ans or raw_ans.strip()
                else:
                    answer = f"Sorry, failed to analyze project context: {q_res.get('error', 'Unknown error')}"

                ui.render_direct_response(answer, elapsed=t_q_elapsed)
                short_term_memory.add_turn(
                    prompt=user_input,
                    category="QUESTION",
                    summary=summary,
                    target_scope=target_scope,
                    direct_response=answer
                )
                continue

            # Layer 2: Planning Loop
            long_term_ctx = long_term_memory.get_formatted_graph_context(target_scope=target_scope)
            contextix_ctx = contextix_adapter.get_relevant_context(target_scope=target_scope, summary=summary)
            agent_state_ctx = contextix_adapter.get_agent_state_context(current_task=summary, current_phase="Planning")
            combined_long_term_ctx = f"{agent_state_ctx}\n\n{contextix_ctx}\n\n{long_term_ctx}".strip()

            revision_feedback: Optional[str] = None
            plan_approved = False
            final_plan = None

            while not plan_approved:
                status_msg = "Constructing execution plan..." if not revision_feedback else "Revising plan based on feedback..."

                with ui.live_status("planner", status_msg) as timer_plan:
                    plan_res = planner.create_plan(
                        intent_data=intent_data,
                        short_term_context=short_term_ctx,
                        long_term_context=combined_long_term_ctx,
                        revision_feedback=revision_feedback
                    )
                t_plan_elapsed = timer_plan["elapsed"]

                if not plan_res["success"]:
                    ui.console.print(f"[bold red]❌ Planning Failed (⏱️ {t_plan_elapsed:.2f}s):[/bold red] {plan_res['error']}")
                    break

                final_plan = plan_res["plan"]
                ui.render_plan(final_plan, elapsed=t_plan_elapsed)

                choice, rev_text = ui.prompt_confirm_plan(len(final_plan.get("steps", [])))
                if choice == "Y":
                    plan_approved = True
                elif choice == "N":
                    ui.console.print("[bold yellow]Plan cancelled by user.[/bold yellow]")
                    break
                elif choice == "R":
                    revision_feedback = rev_text

            if not plan_approved or not final_plan:
                continue

            # Layer 3: Executor
            t_exec_start = time.time()
            steps = final_plan.get("steps", [])

            completed_count = 0
            execution_summaries = []
            step_results = []

            for step in steps:
                step_num = step.get("step_number", 0)
                action = step.get("action_type", "")
                desc = step.get("description", "")

                layer_name = "codegen" if action in ("write_file", "edit_file", "generate_code") else "executor"
                step_msg = f"Executing step {step_num}: {desc}"

                with ui.live_status(layer_name, step_msg) as timer_step:
                    res = executor.execute_step(step, project_root=working_dir)
                t_step_elapsed = timer_step["elapsed"]

                ui.render_step_result(step_num, action, res, elapsed=t_step_elapsed)
                step_results.append(res)

                if res["success"]:
                    completed_count += 1
                    execution_summaries.append(f"Step {step_num} [{action}]: Success")
                    if action in ("write_file", "edit_file", "generate_code"):
                        contextix_adapter.mark_dirty()
                elif res.get("is_response_only"):
                    completed_count += 1
                    execution_summaries.append(f"Step {step_num} [{action}]: Response Only")
                else:
                    execution_summaries.append(f"Step {step_num} [{action}]: Failed ({res.get('error')})")
                    ui.console.print(f"[bold red]Execution stopped at step {step_num}.[/bold red]")
                    break

            t_exec_total = round(time.time() - t_exec_start, 2)
            exec_full_summary = f"{completed_count}/{len(steps)} steps succeeded."

            # Layer 1 Final Task Summary
            if len(step_results) > 0:
                step_logs = []
                for s, r in zip(steps[:len(step_results)], step_results):
                    s_num = s.get("step_number")
                    act = s.get("action_type")
                    out = r.get("output", "") or r.get("code_content", "") or ("Success" if r.get("success") else "Failed")
                    if len(out) > 500: out = out[:500] + "..."
                    
                    if r.get("is_response_only"):
                        step_logs.append(f"Step #{s_num} [{act}] (RESPONSE ONLY - NO EXECUTION EVIDENCE):\n{out}")
                    elif r.get("success"):
                        step_logs.append(f"Step #{s_num} [{act}] (SUCCESSFUL EXECUTION):\n{out}")
                    else:
                        step_logs.append(f"Step #{s_num} [{act}] (FAILED EXECUTION):\n{r.get('error')}")

                sum_system = (
                    "You are the Dinggo project assistant. Your task is to synthesize a clear, comprehensive final executive summary report "
                    "for the user based on the technical step execution findings.\n"
                    "Format your final output cleanly using professional Markdown."
                )
                sum_prompt = (
                    f"Original User Request: {user_input}\n"
                    f"Internal Technical Intent: {summary}\n\n"
                    f"Technical Step Findings:\n" + "\n\n".join(step_logs) + 
                    f"\n\nBased on the Original User Request, synthesize a final executive summary report. "
                    f"CRITICAL: You MUST write this final report entirely in the '{user_language}' language! "
                    "Do not use English unless the user's language is English."
                )

                with ui.live_status("intent", "Synthesizing final executive summary report...") as timer_sum:
                    sum_res = ollama_client.generate(
                        model=intent_parser.model_name,
                        prompt=sum_prompt,
                        system_prompt=sum_system,
                        json_format=False,
                        think=False,
                        temperature=0.3,
                        num_ctx=4096,
                        num_predict=512
                    )
                t_sum_elapsed = timer_sum["elapsed"]

                if sum_res.get("success"):
                    ui.render_direct_response(sum_res["response"].strip(), elapsed=t_sum_elapsed)

            short_term_memory.add_turn(
                prompt=user_input, category="TASK", summary=summary,
                target_scope=target_scope, execution_summary=exec_full_summary
            )

            long_term_memory.build_code_graph()
            if completed_count > 0:
                contextix_adapter.refresh_post_execution(execution_summaries)

            ui.console.print(f"\n[bold green]Completed · {completed_count}/{len(steps)} steps[/bold green] [dim](⏱️ {t_exec_total:.1f}s)[/dim]")

        except KeyboardInterrupt:
            ui.console.print("\n[bold yellow]⚠️ Operation cancelled by user.[/bold yellow]")
            continue


if __name__ == "__main__":
    main()
