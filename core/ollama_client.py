import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class OllamaClient:
    """
    HTTP REST Client for interacting with local Ollama instance.
    Includes explicit keep_alive: 0 unloading logic for RAM safety (<16GB).
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.force_unload = os.getenv("FORCE_UNLOAD_BETWEEN_LAYERS", "true").lower() == "true"
        self.active_model: Optional[str] = None

    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            res = httpx.get(f"{self.base_url}/api/version", timeout=3.0)
            return res.status_code == 200
        except Exception:
            return False

    def unload_model(self, model_name: str) -> bool:
        """
        Forces Ollama to immediately unload model from RAM by sending keep_alive: 0.
        """
        try:
            payload = {
                "model": model_name,
                "keep_alive": 0
            }
            httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=5.0)
            if self.active_model == model_name:
                self.active_model = None
            return True
        except Exception:
            return False

    def generate(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_format: bool = False,
        temperature: float = 0.2,
        top_p: float = 0.9,
        num_ctx: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Sends generation request to Ollama. Automatically unloads active model first if changing models.
        """
        if self.force_unload and self.active_model and self.active_model != model:
            self.unload_model(self.active_model)

        options: Dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p
        }
        if num_ctx:
            options["num_ctx"] = num_ctx

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }

        if system_prompt:
            payload["system"] = system_prompt

        if json_format:
            payload["format"] = "json"

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
            self.active_model = model
            return {
                "success": True,
                "response": data.get("response", ""),
                "done": data.get("done", True)
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"Ollama HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": f"Gagal menghubungi Ollama ({model}): {str(e)}"}
