import os
import httpx
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()


class OllamaClient:
    """
    HTTP REST Client for interacting with local Ollama instance.
    Includes model tag resolution from /api/tags and keep_alive: 0 memory eviction.
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

    def list_installed_models(self) -> List[str]:
        """Fetch list of installed model names from /api/tags."""
        try:
            res = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            pass
        return []

    def resolve_model_name(self, model_name: str) -> str:
        """
        Resolves model_name against installed models in Ollama using exact or fuzzy substring match.
        """
        installed = self.list_installed_models()
        if not installed:
            return model_name

        # Exact match
        if model_name in installed:
            return model_name

        # Case-insensitive exact match
        for m in installed:
            if m.lower() == model_name.lower():
                return m

        # Substring / keyword match (e.g. 'gemma-sea-lion' -> 'hf.co/aisingapore/Gemma-SEA-LION...')
        cleaned_target = model_name.lower().replace("-", "").replace("_", "").replace(":", "")
        for m in installed:
            cleaned_m = m.lower().replace("-", "").replace("_", "").replace(":", "")
            if cleaned_target in cleaned_m or cleaned_m in cleaned_target:
                return m

        return model_name

    def unload_model(self, model_name: str) -> bool:
        """
        Forces Ollama to immediately unload model from RAM by sending keep_alive: 0.
        """
        try:
            resolved = self.resolve_model_name(model_name)
            payload = {
                "model": resolved,
                "keep_alive": 0
            }
            httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=5.0)
            if self.active_model:
                active_resolved = self.resolve_model_name(self.active_model)
                if active_resolved == resolved or self.active_model == model_name or self.active_model == resolved:
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
        num_ctx: Optional[int] = None,
        num_predict: Optional[int] = None,
        think: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Sends generation request to Ollama with auto-resolved model tag name.

        `think`: pass True/False to explicitly control Ollama's native reasoning
        separation (newer Ollama versions return reasoning content in a separate
        `thinking` field for reasoning-capable models like Qwen3.x, instead of
        inline <think> tags). Leave None to use the model's default behavior.
        """
        resolved_model = self.resolve_model_name(model)

        if self.force_unload and self.active_model and self.active_model != resolved_model:
            self.unload_model(self.active_model)

        options: Dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p
        }
        if num_ctx:
            options["num_ctx"] = num_ctx
        # -1 = generate until natural stop / context limit instead of Ollama's
        # short default num_predict, which can truncate a reasoning model mid-think
        # and leave "response" empty.
        options["num_predict"] = num_predict if num_predict is not None else -1

        num_gpu = os.getenv("OLLAMA_NUM_GPU", "99")
        if num_gpu:
            try:
                options["num_gpu"] = int(num_gpu)
            except ValueError:
                pass

        num_thread = os.getenv("OLLAMA_NUM_THREAD")
        if num_thread:
            try:
                options["num_thread"] = int(num_thread)
            except ValueError:
                pass

        payload: Dict[str, Any] = {
            "model": resolved_model,
            "prompt": prompt,
            "stream": False,
            "options": options
        }

        if system_prompt:
            payload["system"] = system_prompt

        if json_format:
            payload["format"] = "json"

        if think is not None:
            payload["think"] = think

        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=180.0
            )
            response.raise_for_status()
            data = response.json()
            self.active_model = resolved_model

            response_text = data.get("response", "")
            thinking_text = data.get("thinking", "")

            # Newer Ollama separates reasoning into `thinking` for models like
            # Qwen3.x. If the model burned its whole budget reasoning and never
            # emitted a final `response`, fall back to `thinking` so callers at
            # least have something to try to parse instead of an empty string.
            used_thinking_fallback = False
            if not response_text.strip() and thinking_text.strip():
                response_text = thinking_text
                used_thinking_fallback = True

            return {
                "success": True,
                "response": response_text,
                "thinking": thinking_text,
                "used_thinking_fallback": used_thinking_fallback,
                "done": data.get("done", True)
            }
        except httpx.HTTPStatusError as e:
            installed = self.list_installed_models()
            avail_str = ", ".join(installed) if installed else "tidak ada"
            return {
                "success": False,
                "error": f"Ollama HTTP {e.response.status_code} ({resolved_model}): {e.response.text}\nModel yang tersedia di Ollama: [{avail_str}]"
            }
        except Exception as e:
            return {"success": False, "error": f"Gagal menghubungi Ollama ({resolved_model}): {str(e)}"}