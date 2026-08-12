import os
import json
import re
import yaml
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError

from core.ollama_client import OllamaClient


class IntentSchema(BaseModel):
    task_type: str = Field(
        default="general_task",
        description="Jenis tugas: create_file, edit_file, read_file, run_command, atau general_task"
    )
    target_scope: List[str] = Field(
        default_factory=list,
        description="Daftar file atau direktori yang relevan"
    )
    summary: str = Field(
        description="Ringkasan maksud/keinginan pengguna"
    )
    constraints: List[str] = Field(
        default_factory=list,
        description="Daftar batasan atau instruksi khusus"
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
    Layer 1: Intent Parsing Wrapper (Gemma-SEA-LION).
    Parses casual user prompt into structured IntentSchema JSON with retry-repair loop.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None, config_path: str = "config/models.yaml"):
        self.client = ollama_client or OllamaClient()
        self.model_name = os.getenv("MODEL_INTENT_PARSER", "gemma-sea-lion")
        self.max_retries = int(os.getenv("MAX_JSON_RETRY", "3"))
        self.system_prompt = self._load_system_prompt(config_path)

    def _load_system_prompt(self, config_path: str) -> str:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    return cfg.get("intent_parser", {}).get("system_prompt", "")
            except Exception:
                pass
        return (
            "Anda adalah modul Intent Parser Dinggo. Parse prompt user ke JSON terstruktur.\n"
            "Format: {\"task_type\": \"...\", \"target_scope\": [], \"summary\": \"...\", \"constraints\": []}"
        )

    def parse(self, user_prompt: str) -> Dict[str, Any]:
        """
        Parses prompt into validated IntentSchema dictionary.
        Executes retry-with-repair loop if LLM outputs malformed JSON.
        """
        current_prompt = user_prompt
        last_error = ""

        for attempt in range(1, self.max_retries + 1):
            if attempt > 1:
                prompt_to_send = (
                    f"Permintaan awal: {user_prompt}\n\n"
                    f"Percobaan sebelumnya (#{attempt-1}) menghasilkan JSON yang tidak valid:\n"
                    f"{last_error}\n\n"
                    f"Perbaiki formatnya dan jawab HANYA dengan JSON valid sesuai skema!"
                )
            else:
                prompt_to_send = current_prompt

            res = self.client.generate(
                model=self.model_name,
                prompt=prompt_to_send,
                system_prompt=self.system_prompt,
                json_format=True,
                temperature=0.1
            )

            if not res["success"]:
                last_error = res.get("error", "Gagal menghubungi Ollama")
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
                last_error = f"Error Parsing/Validation: {str(e)}\nRaw Response: {raw_response[:200]}"

        return {
            "success": False,
            "error": f"Intent Parser gagal menghasilkan JSON valid setelah {self.max_retries} percobaan. Detail: {last_error}",
            "intent": None
        }
