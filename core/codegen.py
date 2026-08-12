import os
import re
import yaml
from typing import Optional, Dict, Any

from core.ollama_client import OllamaClient


def extract_content_block(text: str, ext: str = "") -> str:
    """Extract code/content block if surrounded by markdown fences, otherwise strip text."""
    text = text.strip()
    match = re.search(r"```(?:[a-z0-9_-]+)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
    else:
        extracted = text

    # Remove accidental Python script wrappers for non-python files (e.g. def generate_readme... with open(...) file.write)
    if ext in (".md", ".markdown", ".json", ".yaml", ".txt", ".html"):
        # If model generated `def generate_...(): with open(...) file.write("# Content...")`
        write_matches = re.findall(r"file\.write\((['\"][\s\S]*?['\"])\)", extracted)
        if write_matches:
            cleaned_lines = []
            for w in write_matches:
                # Clean python string quotes/escapes
                try:
                    s = eval(w)
                    cleaned_lines.append(s)
                except Exception:
                    cleaned_lines.append(w.strip("'\"").replace("\\n", "\n"))
            return "".join(cleaned_lines).strip()

    return extracted


class CodegenDelegate:
    """
    Codegen Delegate Wrapper (Qwen2.5-Coder-3b).
    Delegates precision code and document content generation for target files.
    Handles both Python code and non-Python documents (Markdown, JSON, YAML).
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
            "Anda adalah pakar pemrogram dan penulis konten teknis. "
            "Hasilkan HANYA isi file yang lengkap dan murni tanpa penjelasan teks di luar file."
        )

    def generate_code(
        self,
        instruction: str,
        existing_code: Optional[str] = None,
        target_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates code or document content based on instruction, target path extension, and optional existing content.
        """
        ext = os.path.splitext(target_path or "")[1].lower()
        is_python = ext == ".py" or not ext

        if is_python:
            prompt = f"Instruksi Pembuatan Kode Python: {instruction}\n"
            if target_path:
                prompt += f"Target File: {target_path}\n"
            if existing_code:
                prompt += f"\nKode Existing Saat Ini:\n```python\n{existing_code}\n```\n"
            prompt += "\nBerikan kode Python yang lengkap untuk mengimplementasikan instruksi di atas."
        else:
            prompt = f"Instruksi Pembuatan Dokumentasi/File ({ext}): {instruction}\n"
            if target_path:
                prompt += f"Target File Path: {target_path}\n"
            if existing_code:
                prompt += f"\nKonten Existing Saat Ini:\n```{ext.strip('.')}\n{existing_code}\n```\n"
            prompt += (
                f"\nPERHATIAN: Target file '{target_path}' adalah file {ext}.\n"
                f"Hasilkan HANYA konten {ext} yang murni secara langsung!\n"
                f"JANGAN membuat program Python `def generate_...` atau `file.write()`, dan JANGAN menulis teks penjelasan di luar dokumen."
            )

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

        content_clean = extract_content_block(res["response"], ext=ext)
        return {
            "success": True,
            "code": content_clean
        }
