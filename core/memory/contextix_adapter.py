import os
import shutil
import subprocess
import time
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.memory.project_context import ProjectContext


class ContextixAdapter:
    """
    Adapter for integrating Contextix AI Project Memory into Dinggo CLI IDE.
    Features:
    - Auto-detection of global `contextix` CLI / package.
    - Startup auto-generation of `.context/` if missing in project root.
    - In-Memory caching with timestamp invalidation for zero redundant disk reads.
    - Post-execution auto-refresh after file modifications to keep project state 100% synced.
    """

    def __init__(self, context: ProjectContext):
        self.context = context
        self.working_dir = os.path.abspath(context.working_dir)
        self.context_dir = os.path.join(self.working_dir, ".context")
        self.bootstrap_path = os.path.join(self.context_dir, "bootstrap.md")
        self.context_yaml_path = os.path.join(self.context_dir, "context.yaml")
        self.summary_path = os.path.join(self.context_dir, "summary.md")

        # In-memory cache & timestamp tracking
        self._cached_formatted_str: Optional[str] = None
        self._last_mtime: float = 0.0

    def is_available(self) -> bool:
        """Check if contextix CLI or python package is available globally."""
        if shutil.which("contextix"):
            return True
        try:
            import contextix  # noqa: F401
            return True
        except ImportError:
            return False

    def has_context(self) -> bool:
        """Check if .context/ directory exists and contains memory files."""
        return os.path.isdir(self.context_dir) and (
            os.path.exists(self.bootstrap_path) or os.path.exists(self.context_yaml_path)
        )

    def run_generate(self) -> Dict[str, Any]:
        """Runs `contextix generate` in the active project working directory."""
        if not self.is_available():
            return {"success": False, "error": "CLI 'contextix' tidak ditemukan di PATH sistem."}

        try:
            # Use subprocess to run global contextix CLI in project root
            cmd = ["contextix", "generate"]
            start_t = time.time()
            res = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=30.0
            )
            elapsed = round(time.time() - start_t, 2)

            if res.returncode == 0:
                self.invalidate_cache()
                return {"success": True, "elapsed": elapsed, "output": res.stdout.strip()}
            else:
                return {"success": False, "error": res.stderr.strip() or res.stdout.strip() or f"Exit code {res.returncode}"}
        except Exception as e:
            return {"success": False, "error": f"Gagal menjalankan contextix generate: {str(e)}"}

    def ensure_context_on_startup(self, ui: Optional[Any] = None) -> bool:
        """
        Auto-detects .context/ on startup.
        If missing and contextix is available, auto-triggers `contextix generate`.
        """
        if self.has_context():
            return True

        if not self.is_available():
            return False

        if ui and hasattr(ui, "console"):
            ui.console.print("\n[bold cyan]💡 Memori .context/ belum terdeteksi. Menjalankan 'contextix generate' otomatis...[/bold cyan]")

        res = self.run_generate()
        if res["success"]:
            if ui and hasattr(ui, "console"):
                ui.console.print(f"[bold green]✓ Memori Contextix berhasil dibuat otomatis ({res['elapsed']}s).[/bold green]\n")
            return True
        else:
            if ui and hasattr(ui, "console"):
                ui.console.print(f"[dim yellow]⚠️ Contextix auto-generate lewati: {res.get('error')}[/dim yellow]\n")
            return False

    def refresh_after_task(self, modified_files: Optional[List[str]] = None) -> bool:
        """
        Automatically refreshes Contextix project memory in the background after task execution if files were changed.
        """
        if not modified_files:
            return False

        if not self.is_available():
            return False

        res = self.run_generate()
        return res["success"]

    def _get_current_mtime(self) -> float:
        """Calculates latest modification timestamp of .context/ files."""
        mtimes = [0.0]
        for p in (self.bootstrap_path, self.context_yaml_path, self.summary_path):
            if os.path.exists(p):
                try:
                    mtimes.append(os.path.getmtime(p))
                except Exception:
                    pass
        return max(mtimes)

    def invalidate_cache(self):
        """Invalidates the in-memory cache."""
        self._cached_formatted_str = None
        self._last_mtime = 0.0

    def get_formatted_context(self) -> str:
        """
        Returns formatted Contextix project memory string for Layer 2 (Planner) prompt injection.
        Uses in-memory caching and timestamp invalidation for zero redundant disk reads.
        """
        if not self.has_context():
            return ""

        current_mtime = self._get_current_mtime()
        if self._cached_formatted_str is not None and current_mtime <= self._last_mtime and self._last_mtime > 0:
            return self._cached_formatted_str

        # Re-read and build context string from disk
        parts = []

        # 1. bootstrap.md
        if os.path.exists(self.bootstrap_path):
            try:
                with open(self.bootstrap_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    if content:
                        parts.append(f"--- Contextix Bootstrap Memory ---\n{content}")
            except Exception:
                pass

        # 2. context.yaml (Decisions, Constraints, Goals)
        if os.path.exists(self.context_yaml_path):
            try:
                with open(self.context_yaml_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        yaml_summary = []
                        proj = data.get("project", {})
                        if proj.get("name"):
                            yaml_summary.append(f"Proyek: {proj.get('name')} - {proj.get('description', '')}")

                        constraints = data.get("constraints", [])
                        if constraints:
                            yaml_summary.append("Hard Constraints Proyek:")
                            for c in constraints:
                                yaml_summary.append(f" - {c if isinstance(c, str) else c.get('rule', str(c))}")

                        decisions = data.get("decisions", [])
                        if decisions:
                            yaml_summary.append("Keputusan Arsitektur Terdaftar:")
                            for d in decisions[:5]:  # Limit top 5 decisions
                                if isinstance(d, dict):
                                    yaml_summary.append(f" - {d.get('what', '')} (Sebab: {d.get('why', '')})")
                                else:
                                    yaml_summary.append(f" - {d}")

                        if yaml_summary:
                            parts.append("--- Contextix Structured Rules & Decisions ---\n" + "\n".join(yaml_summary))
            except Exception:
                pass

        formatted = "\n\n".join(parts).strip()
        self._cached_formatted_str = formatted
        self._last_mtime = current_mtime
        return formatted

    def get_status(self) -> Dict[str, Any]:
        """Returns metadata summary for Contextix status display."""
        available = self.is_available()
        has_ctx = self.has_context()

        decisions_count = 0
        constraints_count = 0
        project_name = self.context.project_name

        if has_ctx and os.path.exists(self.context_yaml_path):
            try:
                with open(self.context_yaml_path, "r", encoding="utf-8", errors="ignore") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        project_name = data.get("project", {}).get("name", project_name)
                        decisions_count = len(data.get("decisions", []))
                        constraints_count = len(data.get("constraints", []))
            except Exception:
                pass

        return {
            "available": available,
            "has_context": has_ctx,
            "context_dir": self.context_dir,
            "project_name": project_name,
            "decisions_count": decisions_count,
            "constraints_count": constraints_count,
            "bootstrap_exists": os.path.exists(self.bootstrap_path),
            "yaml_exists": os.path.exists(self.context_yaml_path)
        }
