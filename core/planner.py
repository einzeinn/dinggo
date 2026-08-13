import os
import json
import re
import yaml
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError

from core.ollama_client import OllamaClient
from core.intent_parser import extract_json_payload


class PlanStep(BaseModel):
    step_number: int = Field(description="Sequential step number")
    description: str = Field(description="Detailed step description")
    action_type: str = Field(
        description="Action type: search_code, view_outline, read_file, write_file, list_dir, edit_file, run_command, generate_code, or general_response"
    )
    target_path: Optional[str] = Field(default=None, description="Target file/directory path if applicable")
    command: Optional[str] = Field(default=None, description="Shell command or search query if action_type=run_command/search_code")
    instruction: Optional[str] = Field(
        default=None,
        description="Specific code generation or modification instruction if action_type=generate_code or edit_file"
    )


class PlanSchema(BaseModel):
    intent_summary: str = Field(description="Summary of the intent being processed")
    steps: List[PlanStep] = Field(default_factory=list, description="Ordered list of execution steps")


def sanitize_thinking_output(text: str) -> str:
    """Strip out <think>...</think> sections produced by Qwen3.5 thinking mode."""
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    return cleaned.strip()


VALID_ACTION_TYPES = {
    "read_file", "write_file", "list_dir", "edit_file", 
    "run_command", "generate_code", "general_response"
}
ACTION_TYPE_MAP = {
    "information_retrieval": "read_file",
    "code_analysis": "read_file",
    "inspect_file": "read_file",
    "analyze_code": "read_file",
    "search_code": "read_file",
    "view_file": "read_file",
    "create_code": "generate_code",
    "modify_file": "edit_file",
    "exec_command": "run_command",
    "shell": "run_command",
    "cmd": "run_command",
    "info": "general_response",
    "explanation": "general_response",
    "component_mapping": "read_file",
    "synthesis_and_reporting": "general_response",
}


def normalize_plan_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes step action_types to valid enum values."""
    if not isinstance(data, dict):
        return data
    steps = data.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                act = str(step.get("action_type", "")).lower().strip()
                if act in ACTION_TYPE_MAP:
                    step["action_type"] = ACTION_TYPE_MAP[act]
                elif act not in VALID_ACTION_TYPES:
                    step["action_type"] = "read_file" if ("file" in act or "code" in act or "dir" in act) else "general_response"
    return data


class Planner:
    """
    Layer 2: Planner / Orchestrator Wrapper (Qwen3.5-4B thinking mode).
    Converts intent & context into structured PlanSchema with thinking tag handling and repair retry loop.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None, config_path: str = "config/models.yaml"):
        self.client = ollama_client or OllamaClient()
        self.model_name = os.getenv("MODEL_PLANNER", "qwen3.5:4b")
        self.max_retries = int(os.getenv("MAX_JSON_RETRY", "3"))
        self.system_prompt = self._load_system_prompt(config_path)

    def _load_system_prompt(self, config_path: str) -> str:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    return cfg.get("planner", {}).get("system_prompt", "")
            except Exception:
                pass
        return (
            "Anda adalah Planner Dinggo. Susun plan terstruktur dalam JSON.\n"
            "Format: {\"intent_summary\": \"...\", \"steps\": [{\"step_number\": 1, \"description\": \"...\", \"action_type\": \"...\", ...}]}"
        )

    def create_plan(
        self,
        intent_data: Dict[str, Any],
        project_context: Optional[str] = None,
        short_term_context: Optional[str] = None,
        long_term_context: Optional[str] = None,
        revision_feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates structured plan from intent data & context.
        Handles thinking tags and executes repair retry loop.
        """
        prompt_content = f"Intent Parsed:\n{json.dumps(intent_data, ensure_ascii=False, indent=2)}\n"
        if short_term_context and short_term_context.strip():
            prompt_content += f"\n[Riwayat Percakapan Terakhir (Short-Term Memory)]:\n{short_term_context}\n"
        if long_term_context and long_term_context.strip():
            prompt_content += f"\n[Struktur & Graph Kode Proyek (Long-Term Memory)]:\n{long_term_context}\n"
        if project_context:
            prompt_content += f"\nKonteks Tambahan Proyek:\n{project_context}\n"
        if revision_feedback:
            prompt_content += f"\nMasukan/Revisi dari Pengguna:\n{revision_feedback}\n"

        prompt_content += "\nSilakan susun rencana langkah-demi-langkah dalam format JSON valid sesuai skema."

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                prompt_to_send = (
                    f"{prompt_content}\n\n"
                    f"Percobaan sebelumnya (#{attempt-1}) gagal menghasilkan JSON valid:\n"
                    f"{last_error}\n\n"
                    f"Perbaiki dan berikan HANYA JSON valid sesuai skema PlanSchema!"
                )
            else:
                prompt_to_send = prompt_content

            res = self.client.generate(
                model=self.model_name,
                prompt=prompt_to_send,
                system_prompt=self.system_prompt,
                json_format=True,
                think=False,
                temperature=0.2,
                num_ctx=4096,
                num_predict=512
            )

            if not res["success"]:
                last_error = res.get("error", "Gagal menghubungi Ollama Planner")
                continue

            raw_response = res["response"]
            sanitized = sanitize_thinking_output(raw_response)
            json_str = extract_json_payload(sanitized)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Attempt to repair truncated JSON
                repaired = repair_truncated_json(json_str)
                try:
                    data = json.loads(repaired)
                except Exception as e:
                    last_error = f"Error Parsing/Validation Plan: {str(e)}\nRaw Response: {sanitized[:200]}"
                    continue

            try:
                data = normalize_plan_data(data)
                validated = PlanSchema(**data)
                return {
                    "success": True,
                    "plan": validated.model_dump(),
                    "attempts": attempt
                }
            except ValidationError as e:
                last_error = f"Error Validation Plan Schema: {str(e)}\nRaw Response: {sanitized[:200]}"

        return {
            "success": False,
            "error": f"Planner gagal menghasilkan JSON valid setelah {self.max_retries} percobaan. Detail: {last_error}",
            "plan": None
        }
