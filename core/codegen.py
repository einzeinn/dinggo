import os
import re
import yaml
from typing import Optional, Dict, Any

from core.ollama_client import OllamaClient


def extract_code_block(text: str) -> str:
    """Extract code block if surrounded by markdown fences, otherwise strip text."""
    text = text.strip()
    match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text


class CodegenDelegate:
    """
    Codegen Delegate Wrapper (Qwen2.5-Coder-3b).
    Delegates precision Python code generation for steps requiring code creation/modification.
    """

    def __init__(self, ollama_client: Optional[OllamaClient] = None, config_path: str = "config/models.yaml"):
        self.client = ollama_client or OllamaClient()
        self.model_name = os.getenv("MODEL_CODEGEN", "qwen2.5-coder:3b")
        self.system_prompt = self._load_system_prompt(config_path)

    def _load_system_prompt(self, config_path: str) -> str:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                    return cfg.get("codegen", {}).get("system_prompt", "")
            except Exception:
                pass
        return (
            "Anda adalah pakar pemrogram Python yang presisi. "
            "Hasilkan HANYA kode Python yang lengkap dan bersih tanpa penjelasan teks di luar kode."
        )

    def generate_code(
        self,
        instruction: str,
        existing_code: Optional[str] = None,
        target_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates Python code based on instruction and optional existing code content.
        """
        prompt = f"Instruksi Pembuatan Kode: {instruction}\n"
        if target_path:
            prompt += f"Target File: {target_path}\n"
        if existing_code:
            prompt += f"\nKode Existing Saat Ini:\n```python\n{existing_code}\n```\n"

        prompt += "\nBerikan kode Python yang lengkap untuk mengimplementasikan instruksi di atas."

        res = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            system_prompt=self.system_prompt,
            json_format=False,
            temperature=0.1
        )

        if not res["success"]:
            return {
                "success": False,
                "error": res.get("error", "Gagal melakukan codegen"),
                "code": ""
            }

        code_clean = extract_code_block(res["response"])
        return {
            "success": True,
            "code": code_clean
        }
