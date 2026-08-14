import os
import json
import re
import yaml
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError, model_validator

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

    @model_validator(mode="after")
    def validate_executable_targets(self):
        act = self.action_type.lower()
        t_path = (self.target_path or "").strip().lower()
        invalid_targets = {"-", "null", "n/a", "none", ""}
        
        if act in ("read_file", "write_file", "edit_file", "generate_code", "view_outline", "search_code"):
            if t_path in invalid_targets:
                raise ValueError("The previous plan contains an executable target only inside the details field. Move the exact target into target_path. Do not change the intended operation.")
        elif act == "list_dir":
            if t_path == "-" or not t_path:
                raise ValueError("The previous plan contains an executable target only inside the details field. Move the exact target into target_path. Do not change the intended operation.")
        elif act == "run_command":
            cmd = (self.command or "").strip()
            if not cmd or cmd == "-":
                raise ValueError("The previous plan contains an executable command only inside the details field. Move the exact command into 'command'. Do not change the intended operation.")
                
        return self


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
                    raise ValueError(f"Invalid action_type '{act}'. Must be one of: {', '.join(VALID_ACTION_TYPES)}")
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
            "You are the Dinggo Planner. Create a structured step-by-step plan in JSON.\n"
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
        prompt_content = f"Parsed Intent:\n{json.dumps(intent_data, ensure_ascii=False, indent=2)}\n"
        if short_term_context and short_term_context.strip():
            prompt_content += f"\n[Recent Conversation History (Short-Term Memory)]:\n{short_term_context}\n"
        if long_term_context and long_term_context.strip():
            prompt_content += f"\n[Project Architecture & File Graph (Long-Term Memory)]:\n{long_term_context}\n"
        if project_context:
            prompt_content += f"\n[Additional Project Context]:\n{project_context}\n"
        if revision_feedback:
            prompt_content += f"\n[User Feedback/Revision Request]:\n{revision_feedback}\n"

        prompt_content += "\nPlease construct a step-by-step execution plan in valid JSON format matching the schema."
        prompt_content += (
            "\nCRITICAL RULES:\n"
            "1. ENTIRE RESPONSE MUST BE IN ENGLISH.\n"
            "2. 'target_path' MUST contain the exact file/directory path ONLY. Do NOT put paths inside 'description'.\n"
            "3. 'command' MUST contain the exact shell command ONLY.\n"
            "4. 'description' MUST contain human-readable explanation ONLY. No executable instructions hiding here.\n"
        )

        last_error = ""
        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                prompt_to_send = (
                    f"{prompt_content}\n\n"
                    f"Previous attempt (#{attempt-1}) failed to produce valid JSON or violated language rules:\n"
                    f"{last_error}\n\n"
                    f"Please fix the errors and provide ONLY valid JSON matching the PlanSchema!"
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
                # Assuming repair_truncated_json exists or we skip
                last_error = f"Error Parsing JSON.\nRaw Response: {sanitized[:200]}"
                continue

            # Deterministic Language Validation
            # Reject if we detect strong Indonesian stopwords isolated by word boundaries
            if re.search(r'\b(yang|dan|di|ke|dari|untuk|pada|ini|itu|dengan|adalah)\b', json_str, re.IGNORECASE):
                last_error = "Validation Error: Indonesian words detected. You MUST write all JSON values in pure English."
                continue

            try:
                data = normalize_plan_data(data)
                validated = PlanSchema(**data)
                return {
                    "success": True,
                    "plan": validated.model_dump(),
                    "attempts": attempt
                }
            except (ValidationError, ValueError) as e:
                last_error = f"Error Validation Plan Schema: {str(e)}\nRaw Response: {sanitized[:200]}"

        return {
            "success": False,
            "error": f"Planner gagal menghasilkan JSON valid setelah {self.max_retries} percobaan. Detail: {last_error}",
            "plan": None
        }
