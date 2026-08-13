import os
from typing import Dict, Any, List, Optional, Callable

from core.ollama_client import OllamaClient
from core.codegen import CodegenDelegate
from core.validator import SemanticValidator
from tools.file_ops import read_file, write_file, list_dir, edit_file, get_unified_diff
from tools.shell_ops import run_command


class Executor:
    """
    Layer 3 Executor & Layer 4 Semantic Validator.
    Iterates plan steps, calls tools, delegates codegen, validates semantic correctness, and executes auto-repair loops.
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
        Intelligently resolves target_path using exact checks, fuzzy workspace matching, and instruction parsing.
        Example: 'README_KESIAPAN.md' -> resolves to 'docs/README_KESIAPAN.md'
                 'kesiapan' -> resolves to 'docs/README_KESIAPAN.md'
        """
        # 1. Clean placeholder strings
        clean_path = str(target_path).strip() if target_path else None
        if clean_path and clean_path.lower() in ("-", "null", "n/a", "none", ""):
            clean_path = None

        # 2. Direct path check
        if clean_path:
            full_path = clean_path if os.path.isabs(clean_path) else os.path.join(project_root, clean_path)
            if os.path.exists(full_path):
                return clean_path

            # Direct path doesn't exist: search workspace for matching filename/basename!
            target_filename = os.path.basename(clean_path).lower()
            target_no_ext = os.path.splitext(target_filename)[0].lower()

            for root, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "build", "dist", "node_modules")]
                for f in files:
                    f_lower = f.lower()
                    rel_file = os.path.relpath(os.path.join(root, f), project_root)
                    if f_lower == target_filename or (target_no_ext and target_no_ext == os.path.splitext(f_lower)[0]):
                        return rel_file

        # 3. Fallback: Parse instruction for workspace file references
        combined_text = f"{clean_path or ''} {instruction}".lower()
        words = [w for w in combined_text.replace("_", " ").replace("-", " ").replace(".", " ").split() if len(w) > 3 and w not in ("file", "coba", "perbaiki", "ubah", "baca", "tulis", "buat", "agar", "isinya", "murni", "dokumen", "asli", "yang", "profesional", "mudah", "dibaca")]
        
        matches = []
        for root, dirs, files in os.walk(project_root):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "build", "dist", "node_modules")]
            for f in files:
                f_lower = f.lower()
                rel_file = os.path.relpath(os.path.join(root, f), project_root)
                if any(w in f_lower for w in words):
                    matches.append(rel_file)

        if matches:
            return matches[0]

        return clean_path

    def execute_step(self, step: Dict[str, Any], project_root: str = ".") -> Dict[str, Any]:
        """
        Executes a single plan step dictionary with semantic validation & auto-repair loop.
        """
        action_type = step.get("action_type", "").lower()
        raw_target_path = step.get("target_path")
        command = step.get("command")
        instruction = step.get("instruction") or step.get("description", "")

        # Intelligently resolve target_path via fuzzy workspace matching
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
            result["success"] = True
            result["output"] = instruction or step.get("description", "Respon umum selesai.")
            return result

        # Fail explicitly if file operation has no resolvable target_path
        if action_type in ("read_file", "write_file", "edit_file", "generate_code") and not target_full_path:
            result["success"] = False
            result["error"] = f"Gagal eksekusi [{action_type}]: Target path file tidak ditentukan oleh Planner dan tidak ditemukan di proyek."
            return result

        # 1. read_file
        if action_type == "read_file":
            res = read_file(target_full_path)
            result["success"] = res["success"]
            if res["success"]:
                result["output"] = res["content"]
            else:
                result["error"] = res["error"]

        # 2. write_file / generate_code / edit_file
        elif action_type in ("write_file", "edit_file", "generate_code"):
            existing_code = ""
            if os.path.exists(target_full_path) and action_type == "edit_file":
                r_res = read_file(target_full_path)
                if r_res["success"]:
                    existing_code = r_res["content"]

            code_content = step.get("content")
            if not code_content:
                cg_res = self.codegen_delegate.generate_code(
                    instruction=instruction,
                    existing_code=existing_code,
                    target_path=target_path
                )
                if not cg_res["success"]:
                    result["error"] = f"Gagal generate konten: {cg_res['error']}"
                    return result
                code_content = cg_res["code"]

            # Initial write
            res = write_file(target_full_path, code_content)
            if not res["success"]:
                result["error"] = res["error"]
                return result

            # --- Layer 4: Semantic Validation & Auto-Repair Loop ---
            val_res = self.validator.validate_file(target_full_path, content=code_content)
            result["validation"] = val_res

            # Auto-Repair Retry Loop if semantic validation failed
            if not val_res["valid"]:
                repair_attempts = 2
                for r_attempt in range(1, repair_attempts + 1):
                    repair_instruction = (
                        f"{instruction}\n\n"
                        f"[PERBAIKAN OTOMATIS #{r_attempt}]\n"
                        f"Hasil pembuatan sebelumnya GAGAL VALIDASI SEMANTIK:\n"
                        f"Alasan: {val_res['reason']}\n"
                        f"Tindakan Disarankan: {val_res['suggested_action']}\n\n"
                        f"Hasilkan ulang konten yang murni dan benar 100%!"
                    )
                    cg_repair = self.codegen_delegate.generate_code(
                        instruction=repair_instruction,
                        existing_code=existing_code,
                        target_path=target_path
                    )
                    if cg_repair["success"]:
                        repaired_code = cg_repair["code"]
                        res = write_file(target_full_path, repaired_code)
                        if res["success"]:
                            val_res = self.validator.validate_file(target_full_path, content=repaired_code)
                            result["validation"] = val_res
                            if val_res["valid"]:
                                code_content = repaired_code
                                break

            if val_res["valid"]:
                result["success"] = True
                result["code_content"] = code_content
                result["output"] = f"File {target_path} berhasil dibuat/diubah & lulus validasi semantik."
                if existing_code:
                    result["diff"] = get_unified_diff(target_full_path, existing_code, code_content)
            else:
                result["success"] = False
                result["error"] = f"Validasi Semantik Gagal: {val_res['reason']}"

        # 3. list_dir
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

        # 4. run_command
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
