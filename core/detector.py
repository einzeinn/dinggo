"""Project stack and AI Provider discovery engine for Dinggo Product Factory."""
import os
import json
import shutil
import urllib.request
from typing import Dict, Any, List


class ProjectDetector:
    """Detects project characteristics, frameworks, package managers, and available AI providers."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def detect(self) -> Dict[str, Any]:
        """Alias for detect_project."""
        return self.detect_project()

    def detect_all(self) -> Dict[str, Any]:
        """Perform comprehensive environment and stack detection."""
        return {
            "project": self.detect_project(),
            "providers": self.detect_providers()
        }

    def detect_project(self) -> Dict[str, Any]:
        """Detect Git status, languages, frameworks, and spec presence."""
        is_git = os.path.isdir(os.path.join(self.root_dir, ".git"))
        has_spec = os.path.isdir(os.path.join(self.root_dir, "spec")) and any(os.scandir(os.path.join(self.root_dir, "spec"))) if os.path.isdir(os.path.join(self.root_dir, "spec")) else False
        has_contextix = os.path.isdir(os.path.join(self.root_dir, ".context"))

        languages: List[str] = []
        frameworks: List[str] = []
        manifests: List[str] = []

        # Node / JS / TS
        pkg_json_path = os.path.join(self.root_dir, "package.json")
        if os.path.isfile(pkg_json_path):
            manifests.append("package.json")
            languages.append("JavaScript/TypeScript")
            try:
                with open(pkg_json_path, "r", encoding="utf-8") as f:
                    pkg_data = json.load(f)
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                if "next" in deps: frameworks.append("Next.js")
                if "react" in deps: frameworks.append("React")
                if "express" in deps: frameworks.append("Express")
                if "vue" in deps: frameworks.append("Vue")
                if "tailwindcss" in deps: frameworks.append("Tailwind CSS")
            except Exception:
                pass

        # Python
        if any(os.path.isfile(os.path.join(self.root_dir, f)) for f in ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile")):
            languages.append("Python")
            if os.path.isfile(os.path.join(self.root_dir, "pyproject.toml")): manifests.append("pyproject.toml")
            if os.path.isfile(os.path.join(self.root_dir, "requirements.txt")): manifests.append("requirements.txt")

            # Check framework signatures
            req_content = ""
            for req_f in ("requirements.txt", "pyproject.toml"):
                p = os.path.join(self.root_dir, req_f)
                if os.path.isfile(p):
                    try:
                        with open(p, "r", encoding="utf-8") as f:
                            req_content += f.read().lower() + "\n"
                    except Exception:
                        pass
            if "fastapi" in req_content: frameworks.append("FastAPI")
            if "django" in req_content: frameworks.append("Django")
            if "flask" in req_content: frameworks.append("Flask")

        # Rust
        if os.path.isfile(os.path.join(self.root_dir, "Cargo.toml")):
            languages.append("Rust")
            manifests.append("Cargo.toml")

        # Go
        if os.path.isfile(os.path.join(self.root_dir, "go.mod")):
            languages.append("Go")
            manifests.append("go.mod")

        # Database hints
        database = None
        compose_path = os.path.join(self.root_dir, "docker-compose.yml")
        if os.path.isfile(compose_path):
            try:
                with open(compose_path, "r", encoding="utf-8") as f:
                    c_txt = f.read().lower()
                if "postgres" in c_txt: database = "PostgreSQL"
                elif "mysql" in c_txt or "mariadb" in c_txt: database = "MySQL/MariaDB"
                elif "mongo" in c_txt: database = "MongoDB"
                elif "redis" in c_txt: database = "Redis"
            except Exception:
                pass

        return {
            "name": os.path.basename(self.root_dir),
            "root_path": self.root_dir,
            "is_git": is_git,
            "has_spec": has_spec,
            "has_contextix": has_contextix,
            "languages": list(set(languages)),
            "frameworks": list(set(frameworks)),
            "manifests": manifests,
            "database": database,
            "type": "Full-Stack Application" if len(languages) > 1 or ("Next.js" in frameworks and "FastAPI" in frameworks) else (languages[0] if languages else "Generic Project")
        }

    def detect_providers(self) -> Dict[str, Any]:
        """Detect local and CLI AI providers."""
        providers = {
            "codex": {"name": "Codex CLI", "available": bool(shutil.which("codex")), "type": "cli"},
            "claude": {"name": "Claude CLI", "available": bool(shutil.which("claude")), "type": "cli"},
            "gemini": {"name": "Gemini / Antigravity CLI", "available": bool(shutil.which("gemini") or shutil.which("agy")), "type": "cli"},
            "ollama": {"name": "Ollama (Local Server)", "available": False, "models": [], "type": "local_server"}
        }

        # Check Ollama HTTP server
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            req = urllib.request.Request(f"{ollama_host}/api/tags", headers={"User-Agent": "Dinggo/0.2.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    providers["ollama"]["available"] = True
                    providers["ollama"]["models"] = models
        except Exception:
            providers["ollama"]["available"] = False

        return providers
