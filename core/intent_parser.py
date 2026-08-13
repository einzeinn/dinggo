import os
import json
import re
import yaml
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError

from core.ollama_client import OllamaClient


class IntentSchema(BaseModel):
    category: str = Field(
        default="TASK",
        description="Intent category: TASK, CONVERSATION, QUESTION, or CLARIFICATION"
    )
    is_task: bool = Field(
        default=True,
        description="True for technical execution/coding/file/command tasks, False for greetings/chat/questions/clarifications"
    )
    task_type: str = Field(
        default="general_task",
        description="Task type: create_file, edit_file, read_file, run_command, general_task, chat, question, or clarification"
    )
    target_scope: List[str] = Field(
        default_factory=list,
        description="List of relevant files or directories"
    )
    summary: str = Field(
        description="Concise summary of user intent"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="List of specific constraints or instructions"
    )
    direct_response: Optional[str] = Field(
        default=None,
        description="Direct response message (CONVERSATION/CLARIFICATION) when is_task=False"
    )


def extract_json_payload(text: str) -> str:
    """Extract JSON string from text, stripping markdown codeblocks if present."""
    text = text.strip()
    # Check for ```json ... ``` codeblocks
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Check for raw JSON object {...}
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        return match.group(1).strip()
        
    return text


class IntentParser:
    """
    Layer 1: Intent Parser Wrapper (Gemma-SEA-LION 4B).
    Parses raw user input into structured Pydantic IntentSchema.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None, config_path: str = "config/models.yaml"):
        self.client = ollama_client or OllamaClient()
        self.model_name = os.getenv("MODEL_INTENT_PARSER", os.getenv("MODEL_INTENT", "hf.co/aisingapore/Gemma-SEA-LION-v4.5-E2B-IT-GGUF:Q4_K_M"))
        self.system_prompt = self._load_system_prompt(config_path)
        self.max_retries = 2

    def _load_system_prompt(self, config_path: str) -> str:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    return cfg.get("intent_parser", {}).get("system_prompt", "")
            except Exception:
                pass
        return "You are the Intent Parser module for the Dinggo CLI IDE."

    def parse(self, user_prompt: str, short_term_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses user prompt into structured JSON payload adhering to IntentSchema.
        Includes automatic retry & self-repair loop up to max_retries.
        """
        if short_term_context:
            current_prompt = f"Short-term Conversation History:\n{short_term_context}\n\nCurrent User Request: {user_prompt}"
        else:
            current_prompt = user_prompt
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                prompt_to_send = (
                    f"Initial request: {user_prompt}\n\n"
                    f"Previous attempt (#{attempt-1}) produced invalid JSON:\n"
                    f"{last_error}\n\n"
                    f"Fix the format and respond ONLY with valid JSON adhering to the schema!"
                )
            else:
                prompt_to_send = current_prompt

            res = self.client.generate(
                model=self.model_name,
                prompt=prompt_to_send,
                system_prompt=self.system_prompt,
                json_format=True,
                think=False,
                temperature=0.1,
                num_ctx=2048,
                num_predict=256
            )

            if not res["success"]:
                last_error = res.get("error", "Failed to contact Ollama")
                continue

            raw_response = res["response"]
            json_str = extract_json_payload(raw_response)

            try:
                data = json.loads(json_str)
                validated = IntentSchema(**data)
                return {
                    "success": True,
                    "intent": validated.model_dump(),
                    "attempts": attempt
                }
            except (json.JSONDecodeError, ValidationError) as e:
                last_error = f"Parsing/Validation Error: {str(e)}\nRaw Response: {raw_response[:200]}"

        return {
            "success": False,
            "error": f"Intent Parser failed to generate valid JSON after {self.max_retries} attempts. Detail: {last_error}",
            "intent": None
        }
