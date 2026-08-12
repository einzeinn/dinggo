import os
from typing import Dict, Any, List, Optional, Callable

from core.ollama_client import OllamaClient
from core.codegen import CodegenDelegate
from tools.file_ops import read_file, write_file, list_dir, edit_file, get_unified_diff
from tools.shell_ops import run_command


class Executor:
    """
    Layer 3 Executor.
    Iterates plan steps, calls tools, delegates Python codegen, and enforces confirmation guards.
    """

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        confirm_command_callback: Optional[Callable[[str], bool]] = None,
        step_progress_callback: Optional[Callable[[int, str, str], None]] = None
    ):
        self.client = ollama_client or OllamaClient()
        self.codegen_delegate = CodegenDelegate(ollama_client=self.client)
        self.confirm_command_callback = confirm_command_callback
        self.step_progress_callback = step_progress_callback

    def execute_step(self, step: Dict[str, Any], project_root: str = ".") -> Dict[str, Any]:
        """
        Executes a single plan step dictionary.
        """
        action_type = step.get("action_type", "").lower()
        target_path = step.get("target_path")
        command = step.get("command")
        instruction = step.get("instruction") or step.get("description", "")

        if target_path and not os.path.isabs(target_path):
            target_path = os.path.join(project_root, target_path)

        result: Dict[str, Any] = {
            "step_number": step.get("step_number"),
            "action_type": action_type,
            "target_path": target_path,
            "success": False,
            "output": "",
            "diff": None,
            "error": None
        }

        # 1. read_file
        if action_type == "read_file":
            if not target_path:
                result["error"] = "Target path tidak ditentukan untuk read_file"
                return result
            res = read_file(target_path)
            result["success"] = res["success"]
            if res["success"]:
                result["output"] = res["content"]
            else:
                result["error"] = res["error"]

        # 2. write_file
        elif action_type == "write_file":
            if not target_path:
                result["error"] = "Target path tidak ditentukan untuk write_file"
                return result
            
            # If step has no explicit code content, generate via Codegen
            code_content = step.get("content")
            if not code_content:
                cg_res = self.codegen_delegate.generate_code(
                    instruction=instruction,
                    target_path=target_path
                )
                if not cg_res["success"]:
                    result["error"] = f"Gagal generate kode: {cg_res['error']}"
                    return result
                code_content = cg_res["code"]

            res = write_file(target_path, code_content)
            result["success"] = res["success"]
            if res["success"]:
                result["output"] = f"File berhasil ditulis: {target_path} ({res['bytes_written']} bytes)"
            else:
                result["error"] = res["error"]

        # 3. list_dir
        elif action_type == "list_dir":
            dir_path = target_path or project_root
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

        # 4. edit_file / generate_code
        elif action_type in ("edit_file", "generate_code"):
            if not target_path:
                result["error"] = f"Target path tidak ditentukan untuk {action_type}"
                return result

            # Read existing file content if file exists
            existing_code = ""
            if os.path.exists(target_path):
                r_res = read_file(target_path)
                if r_res["success"]:
                    existing_code = r_res["content"]

            cg_res = self.codegen_delegate.generate_code(
                instruction=instruction,
                existing_code=existing_code,
                target_path=target_path
            )

            if not cg_res["success"]:
                result["error"] = f"Gagal generate/edit kode: {cg_res['error']}"
                return result

            new_code = cg_res["code"]
            diff_str = get_unified_diff(target_path, existing_code, new_code)
            
            res = write_file(target_path, new_code)
            result["success"] = res["success"]
            if res["success"]:
                result["diff"] = diff_str
                result["output"] = f"File {target_path} berhasil diubah."
            else:
                result["error"] = res["error"]

        # 5. run_command (Mandatory explicit user confirmation safety guard)
        elif action_type == "run_command":
            if not command:
                result["error"] = "Command string tidak ditentukan untuk run_command"
                return result

            # Check for user confirmation
            if self.confirm_command_callback:
                approved = self.confirm_command_callback(command)
                if not approved:
                    result["success"] = False
                    result["error"] = f"Eksekusi command DIBATALKAN oleh pengguna: {command}"
                    return result

            res = run_command(command, cwd=project_root)
            result["success"] = res["success"]
            result["output"] = f"STDOUT:\n{res['stdout']}\nSTDERR:\n{res['stderr']}"
            if not res["success"]:
                result["error"] = f"Command keluar dengan return code {res['returncode']}"

        else:
            result["error"] = f"Action type tidak dikenal: {action_type}"

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

            if not res["success"]:
                overall_success = False
                break  # Stop execution on failure

        return {
            "success": overall_success,
            "total_steps": len(steps),
            "executed_count": len(executed_results),
            "results": executed_results
        }
