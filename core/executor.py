import os
from typing import Dict, Any, List, Optional, Callable

from core.ollama_client import OllamaClient
from core.codegen import CodegenDelegate
from core.validator import SemanticValidator
from tools.file_ops import read_file, write_file, list_dir, edit_file, get_unified_diff, search_code, view_outline
from tools.shell_ops import run_command


class Executor:
    """
    Layer 3 Executor & Layer 4 Semantic Validator.
    Iterates plan steps, calls tools, delegates codegen, validates syntax & semantic correctness,
    executes max 2 repair retries, and performs safe rollback to original content on double failure.
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        confirm_command_callback: Optional[Callable[[str], bool]] = None,
        step_progress_callback: Optional[Callable[[int, str, str], None]] = None
    ):
        self.client = ollama_client or OllamaClient()
        self.codegen_delegate = CodegenDelegate(ollama_client=self.client)
        self.validator = SemanticValidator()
        self.confirm_command_callback = confirm_command_callback
        self.step_progress_callback = step_progress_callback

    def resolve_target_path(self, target_path: Optional[str], instruction: str, project_root: str = ".") -> Optional[str]:
        """
        Resolves target_path strictly. 
        Does NOT perform fuzzy workspace matching or instruction regex guessing.
        Returns the resolved path if it's a valid relative or absolute path, else None.
        """
        clean_path = str(target_path).strip() if target_path else None
        if clean_path and clean_path.lower() in ("-", "null", "n/a", "none", ""):
            return None

        if clean_path:
            full_path = clean_path if os.path.isabs(clean_path) else os.path.join(project_root, clean_path)
            if os.path.exists(full_path):
                return clean_path
                
        return clean_path

    def execute_step(self, step: Dict[str, Any], project_root: str = ".") -> Dict[str, Any]:
        """
        Executes a single plan step dictionary with syntax validation, max 2 repair retries, and safe rollback.
        """
        action_type = step.get("action_type", "").lower()
        raw_target_path = step.get("target_path")
        command = step.get("command")
        instruction = step.get("instruction") or step.get("description", "")

        target_path = self.resolve_target_path(raw_target_path, instruction, project_root=project_root)

        if target_path and not os.path.isabs(target_path):
            target_full_path = os.path.join(project_root, target_path)
        else:
            target_full_path = target_path

        result: Dict[str, Any] = {
            "step_number": step.get("step_number"),
            "action_type": action_type,
            "target_path": target_path or raw_target_path,
            "success": False,
            "output": "",
            "diff": None,
            "error": None,
            "validation": None
        }

        # 0. general_response handling
        if action_type in ("general_response", "respond", "info", "general_task", "none"):
            result["success"] = False  # Not an execution success
            result["is_response_only"] = True
            desc = instruction or step.get("description", "General response step.")
            result["output"] = f"{desc}\n[WARNING: This is a general response step. NO files were read and NO execution evidence was gathered.]"
            return result

        # Fail explicitly if executable action has no target_path
        if action_type in ("read_file", "write_file", "edit_file", "generate_code", "view_outline"):
            if not target_path or not target_full_path:
                result["success"] = False
                result["error"] = f"Execution failed [{action_type}]: Target file path was missing, explicitly invalid, or not specified by Planner."
                return result
                
            if action_type in ("read_file", "view_outline") and not os.path.exists(target_full_path):
                result["success"] = False
                result["error"] = f"Target path '{raw_target_path}' not found. You must specify a valid file path, or use 'list_dir' to find files."
                return result

        # 1. read_file
        if action_type == "read_file":
            res = read_file(target_full_path)
            result["success"] = res["success"]
            if res["success"]:
                result["output"] = res["content"]
            else:
                result["error"] = res["error"]

        # 2. search_code
        elif action_type == "search_code":
            search_query = command or instruction or raw_target_path or ""
            res = search_code(query=search_query, root_dir=project_root)
            result["success"] = res["success"]
            result["output"] = res.get("output", "")
            if not res["success"]:
                result["error"] = res.get("error")

        # 3. view_outline
        elif action_type == "view_outline":
            res = view_outline(target_full_path)
            result["success"] = res["success"]
            result["output"] = res.get("output", "")
            if not res["success"]:
                result["error"] = res.get("error")

        # 4. write_file / generate_code / edit_file
        elif action_type in ("write_file", "edit_file", "generate_code"):
            # Retain original content for safe rollback on failed validation
            original_content: Optional[str] = None
            if target_full_path and os.path.exists(target_full_path):
                r_res = read_file(target_full_path)
                if r_res["success"]:
                    original_content = r_res["content"]

            code_content = step.get("content")
            if not code_content:
                cg_res = self.codegen_delegate.generate_code(
                    instruction=instruction,
                    existing_code=original_content or "",
                    target_path=target_path
                )
                if not cg_res["success"]:
                    result["error"] = f"Failed to generate content: {cg_res['error']}"
                    return result
                code_content = cg_res["code"]

            # Perform initial file write/edit
            if action_type == "edit_file":
                res = edit_file(target_full_path, code_content)
                if not res["success"]:
                    result["error"] = res["error"]
                    return result
                code_content = res.get("code_content", code_content)
            else:
                res = write_file(target_full_path, code_content)
                if not res["success"]:
                    result["error"] = res["error"]
                    return result

            # --- Syntax & Semantic Validation ---
            syn_val = self.validator.validate_syntax(target_full_path, code_content)
            result["validation"] = syn_val

            # Closed-Loop Repair (Max 2 Attempts)
            if not syn_val["valid"]:
                max_repairs = 2
                repair_success = False

                for r_attempt in range(1, max_repairs + 1):
                    repair_res = self.codegen_delegate.repair_code(
                        target_path=target_path or "",
                        validation_error=syn_val["message"],
                        relevant_code=code_content,
                        original_task=instruction
                    )
                    if repair_res["success"]:
                        repaired_patch = repair_res["code"]
                        if "<<<<<<< SEARCH" in repaired_patch:
                            e_res = edit_file(target_full_path, repaired_patch)
                            if e_res["success"]:
                                code_content = e_res.get("code_content", code_content)
                        else:
                            w_res = write_file(target_full_path, repaired_patch)
                            if w_res["success"]:
                                code_content = repaired_patch

                        syn_val = self.validator.validate_syntax(target_full_path, code_content)
                        result["validation"] = syn_val
                        if syn_val["valid"]:
                            repair_success = True
                            break

                # SAFE ROLLBACK if both repair attempts failed
                if not repair_success:
                    if original_content is not None:
                        write_file(target_full_path, original_content)
                    elif os.path.exists(target_full_path):
                        os.remove(target_full_path)

                    result["success"] = False
                    result["rolled_back"] = True
                    result["reason"] = "validation_failed_after_2_repairs"
                    result["error"] = f"Syntax validation failed after 2 repair attempts ({syn_val['message']}). File restored to original state (rolled back)."
                    return result

            result["success"] = True
            result["code_content"] = code_content
            result["output"] = f"File {target_path} successfully written/modified & passed syntax validation."
            if original_content is not None:
                result["diff"] = get_unified_diff(target_full_path, original_content, code_content)

        # 5. list_dir
        elif action_type == "list_dir":
            dir_path = target_full_path or project_root
            res = list_dir(dir_path)
            result["success"] = res["success"]
            if res["success"]:
                items_str = "\n".join(
                    f"[{'DIR' if item['is_dir'] else 'FILE'}] {item['name']}"
                    for item in res["items"]
                )
                result["output"] = items_str
            else:
                result["error"] = res["error"]

        # 6. run_command
        elif action_type == "run_command":
            if not command:
                result["error"] = "Command string not specified for run_command"
                return result

            if self.confirm_command_callback:
                approved = self.confirm_command_callback(command)
                if not approved:
                    result["success"] = False
                    result["error"] = f"Command execution CANCELLED by user: {command}"
                    return result

            res = run_command(command, cwd=project_root)
            result["success"] = res["success"]
            result["output"] = f"STDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"
            if not res["success"]:
                result["error"] = f"Command exited with return code {res['returncode']}"

        else:
            result["error"] = f"Unknown action type: {action_type}"

        return result

    def execute_plan(self, plan: Dict[str, Any], project_root: str = ".") -> Dict[str, Any]:
        """
        Executes all steps in the plan sequentially.
        """
        steps = plan.get("steps", [])
        executed_results: List[Dict[str, Any]] = []
        overall_success = True

        for step in steps:
            step_num = step.get("step_number", 0)
            desc = step.get("description", "")
            action = step.get("action_type", "")

            if self.step_progress_callback:
                self.step_progress_callback(step_num, action, desc)

            res = self.execute_step(step, project_root=project_root)
            executed_results.append(res)

            if not res["success"] and not res.get("is_response_only"):
                overall_success = False
                break  # Stop execution on failure

        return {
            "success": overall_success,
            "total_steps": len(steps),
            "executed_count": len(executed_results),
            "results": executed_results
        }
