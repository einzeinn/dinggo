import os
import sys
import shutil
import subprocess
import time
import threading
import yaml
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from core.memory.project_context import ProjectContext


class ContextState(str, Enum):
    CLEAN = "CLEAN"
    DIRTY = "DIRTY"
    REFRESHING = "REFRESHING"


class ContextixAdapter:
    """
    Adapter for integrating Contextix AI Project Memory into Dinggo CLI IDE.
    Implements:
    - State Machine: CLEAN, DIRTY, REFRESHING.
    - Decoupled Memory: Context Cache (Contextix docs/decisions) vs Agent State (Dinggo task/plan runtime).
    - Scope-Targeted Context Querying: Filters relevant subsets of decisions/rules for 4K context window.
    - Non-blocking Post-Task Batch Refresh: Refresh triggered ONCE after execution completes (no per-step refresh loops).
    """

    def __init__(self, context: ProjectContext):
        self.context = context
        self.working_dir = os.path.abspath(context.working_dir)
        self.context_dir = os.path.join(self.working_dir, ".context")
        self.bootstrap_path = os.path.join(self.context_dir, "bootstrap.md")
        self.context_yaml_path = os.path.join(self.context_dir, "context.yaml")
        self.summary_path = os.path.join(self.context_dir, "summary.md")

        # State Machine & Threading
        self.state: ContextState = ContextState.CLEAN if self.has_context() else ContextState.DIRTY
        self._refresh_lock = threading.Lock()

        # In-memory cache & timestamp tracking
        self._cached_context_data: Optional[Dict[str, Any]] = None
        self._cached_formatted_str: Optional[str] = None
        self._last_mtime: float = 0.0

    def is_available(self) -> bool:
        """Check if contextix python package or CLI executable is available."""
        try:
            from contextix.core import generate_memory  # noqa: F401
            return True
        except ImportError:
            pass
        return shutil.which("contextix") is not None

    def has_context(self) -> bool:
        """Check if .context/ directory exists and contains memory files."""
        return os.path.isdir(self.context_dir) and (
            os.path.exists(self.bootstrap_path) or os.path.exists(self.context_yaml_path)
        )

    def mark_dirty(self):
        """Marks the context memory state as DIRTY when files are modified by Executor."""
        if self.state != ContextState.REFRESHING:
            self.state = ContextState.DIRTY

    def run_generate(self) -> Dict[str, Any]:
        """Synchronously runs Contextix memory generation for active project working directory."""
        if not self.is_available():
            return {"success": False, "error": "Modul / CLI 'contextix' tidak terpasang di environment."}

        start_t = time.time()

        # Method 1: Direct Python API call (fastest, cross-platform, zero subprocess overhead)
        try:
            from pathlib import Path as _Path
            from contextix.core import generate_memory
            generate_memory(_Path(self.working_dir))
            elapsed = round(time.time() - start_t, 2)
            self.invalidate_cache()
            self.state = ContextState.CLEAN
            return {"success": True, "elapsed": elapsed, "output": "Direct Python API generate_memory completed."}
        except Exception as e_api:
            api_error = str(e_api)

        # Method 2: Subprocess via the interpreter that has contextix installed
        # Detect interpreter that owns contextix package to avoid cross-environment PATH issues
        try:
            import contextix as _ctx_mod
            import inspect
            ctx_python = os.path.join(
                os.path.dirname(os.path.dirname(inspect.getfile(_ctx_mod))),
                "Scripts", "python.exe"
            )
            if not os.path.exists(ctx_python):
                ctx_python = None
        except Exception:
            ctx_python = None

        # Build fallback command list: contextix-env python > sys.executable > global CLI
        cmds = []
        if ctx_python:
            cmds.append([ctx_python, "-m", "contextix", "generate"])
        cmds.append([sys.executable, "-m", "contextix", "generate"])
        cmds.append(["contextix", "generate"])

        last_error = api_error

        for cmd in cmds:
            try:
                res = subprocess.run(
                    cmd,
                    cwd=self.working_dir,
                    capture_output=True,
                    text=True,
                    timeout=35.0
                )
                elapsed = round(time.time() - start_t, 2)
                if res.returncode == 0:
                    self.invalidate_cache()
                    self.state = ContextState.CLEAN
                    return {"success": True, "elapsed": elapsed, "output": res.stdout.strip()}
                else:
                    last_error = res.stderr.strip() or res.stdout.strip() or f"Exit code {res.returncode}"
            except subprocess.TimeoutExpired:
                last_error = f"Timeout setelah 35s saat menjalankan: {' '.join(cmd)}"
                continue
            except Exception as ex:
                last_error = str(ex)

        return {"success": False, "error": f"Gagal menjalankan contextix generate: {last_error}"}

    def refresh_post_execution(self, modified_files: Optional[List[str]] = None):
        """
        Triggers a non-blocking post-execution batch refresh after Executor completes all steps.
        Transitions state: DIRTY -> REFRESHING -> CLEAN.
        Does NOT block if user sends a new prompt during REFRESHING.
        """
        if not self.is_available():
            return

        if self.state == ContextState.CLEAN and self.has_context():
            return

        def _bg_refresh():
            with self._refresh_lock:
                self.state = ContextState.REFRESHING
                res = self.run_generate()
                if res["success"]:
                    self.state = ContextState.CLEAN
                else:
                    self.state = ContextState.DIRTY

        thread = threading.Thread(target=_bg_refresh, daemon=True)
        thread.start()

    def ensure_context_on_startup(self, ui: Optional[Any] = None) -> bool:
        """
        Auto-detects .context/ on startup.
        If missing and contextix is available, auto-triggers initial `contextix generate`.
        """
        if self.has_context():
            self.state = ContextState.CLEAN
            return True

        if not self.is_available():
            self.state = ContextState.DIRTY
            return False

        if ui and hasattr(ui, "console"):
            ui.console.print("\n[bold cyan]💡 Memori .context/ belum terdeteksi. Menjalankan 'contextix generate' otomatis...[/bold cyan]")

        res = self.run_generate()
        if res["success"]:
            self.state = ContextState.CLEAN
            if ui and hasattr(ui, "console"):
                ui.console.print(f"[bold green]✓ Memori Contextix berhasil dibuat otomatis ({res['elapsed']}s).[/bold green]\n")
            return True
        else:
            self.state = ContextState.DIRTY
            if ui and hasattr(ui, "console"):
                ui.console.print(f"[dim yellow]⚠️ Contextix auto-generate lewati: {res.get('error')}[/dim yellow]\n")
            return False

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
        self._cached_context_data = None
        self._cached_formatted_str = None
        self._last_mtime = 0.0

    def _load_raw_data(self) -> Dict[str, Any]:
        """Loads and parses raw yaml and markdown data from disk with mtime check."""
        current_mtime = self._get_current_mtime()
        if self._cached_context_data is not None and current_mtime <= self._last_mtime and self._last_mtime > 0:
            return self._cached_context_data

        data: Dict[str, Any] = {
            "bootstrap": "",
            "constraints": [],
            "decisions": [],
            "project_name": self.context.project_name
        }

        if os.path.exists(self.bootstrap_path):
            try:
                with open(self.bootstrap_path, "r", encoding="utf-8", errors="ignore") as f:
                    data["bootstrap"] = f.read().strip()
            except Exception:
                pass

        if os.path.exists(self.context_yaml_path):
            try:
                with open(self.context_yaml_path, "r", encoding="utf-8", errors="ignore") as f:
                    y_data = yaml.safe_load(f)
                    if isinstance(y_data, dict):
                        proj = y_data.get("project", {})
                        if proj.get("name"):
                            data["project_name"] = proj.get("name")
                        data["constraints"] = y_data.get("constraints", [])
                        data["decisions"] = y_data.get("decisions", [])
            except Exception:
                pass

        self._cached_context_data = data
        self._last_mtime = current_mtime
        return data

    def get_relevant_context(self, target_scope: Optional[List[str]] = None, summary: str = "") -> str:
        """
        Target-Scope Relevant Querying:
        Instead of dumping the entire .context/ directory (which bloats 4K context windows),
        extracts ONLY the relevant subset:
        1. Always include Hard Constraints.
        2. Filter Decisions & Bootstrap sections matching keywords in target_scope or summary.
        """
        if not self.has_context():
            return ""

        data = self._load_raw_data()
        scope_keywords = set()
        if target_scope:
            for s in target_scope:
                clean_s = os.path.basename(s).lower().replace(".", " ").replace("_", " ").replace("-", " ")
                scope_keywords.update(w for w in clean_s.split() if len(w) > 2)

        summary_words = [w.lower() for w in summary.split() if len(w) > 3]
        scope_keywords.update(summary_words)

        parts = []

        # 1. Hard Constraints (Always included)
        constraints = data.get("constraints", [])
        if constraints:
            c_lines = ["--- Contextix Project Constraints (Hard Rules) ---"]
            for c in constraints:
                c_str = c if isinstance(c, str) else c.get("rule", str(c))
                c_lines.append(f" • {c_str}")
            parts.append("\n".join(c_lines))

        # 2. Targeted Decisions (Filtered by scope keywords if keywords exist, otherwise top decisions)
        decisions = data.get("decisions", [])
        if decisions:
            relevant_decisions = []
            for d in decisions:
                d_str = str(d).lower()
                if not scope_keywords or any(kw in d_str for kw in scope_keywords):
                    if isinstance(d, dict):
                        relevant_decisions.append(f" • {d.get('what', '')} (Why: {d.get('why', '')})")
                    else:
                        relevant_decisions.append(f" • {d}")

            if not relevant_decisions:  # Fallback to top 3 decisions if no specific keyword matched
                for d in decisions[:3]:
                    if isinstance(d, dict):
                        relevant_decisions.append(f" • {d.get('what', '')} (Why: {d.get('why', '')})")
                    else:
                        relevant_decisions.append(f" • {d}")

            if relevant_decisions:
                parts.append("--- Contextix Relevant Decisions ---\n" + "\n".join(relevant_decisions[:4]))

        # 3. Targeted Bootstrap excerpt (first 500 chars if present)
        bootstrap = data.get("bootstrap", "")
        if bootstrap and len(bootstrap) > 20:
            excerpt = bootstrap[:600] + ("..." if len(bootstrap) > 600 else "")
            parts.append(f"--- Contextix Bootstrap Overview ---\n{excerpt}")

        return "\n\n".join(parts).strip()

    def get_agent_state_context(
        self,
        current_task: str = "",
        current_phase: str = "Planning",
        completed_actions: Optional[List[str]] = None
    ) -> str:
        """
        Formats active Dinggo Agent State (runtime state distinct from Contextix context cache).
        """
        state_lines = [
            f"--- Dinggo Active Agent State ---",
            f"Task: {current_task or 'General'}",
            f"Phase: {current_phase}",
            f"Context Memory State: {self.state.value}"
        ]
        if completed_actions:
            state_lines.append("Aksi Terakhir: " + ", ".join(completed_actions[-3:]))
        return "\n".join(state_lines)

    def get_status(self) -> Dict[str, Any]:
        """Returns metadata summary and current state machine status for UI display."""
        available = self.is_available()
        has_ctx = self.has_context()
        data = self._load_raw_data() if has_ctx else {}

        return {
            "state": self.state.value,
            "available": available,
            "has_context": has_ctx,
            "context_dir": self.context_dir,
            "project_name": data.get("project_name", self.context.project_name),
            "decisions_count": len(data.get("decisions", [])),
            "constraints_count": len(data.get("constraints", [])),
            "bootstrap_exists": os.path.exists(self.bootstrap_path),
            "yaml_exists": os.path.exists(self.context_yaml_path)
        }
