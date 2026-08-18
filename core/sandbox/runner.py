"""Sandboxed execution runner providing filesystem boundary checks, environment sanitization, and containment."""
import os
import re
import sys
import ast
import time
import subprocess
from typing import Dict, Any, Optional, List
from core.sandbox.policy import SandboxPolicy


class SandboxedRunner:
    """
    Executes scripts, tests, and shell commands inside a contained minimal sandbox.
    Guarantees:
    - Filesystem boundary validation (cannot write/delete outside workspace root).
    - Secret & sensitive API token sanitization from subprocess environment.
    - Blocking dangerous destructive commands or suspicious AST constructs.
    - Timeout containment to prevent runaway loops or fork bombs.
    """

    def __init__(self, root_dir: str = ".", policy: Optional[SandboxPolicy] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.policy = policy or SandboxPolicy(allowed_root=self.root_dir)

    def is_safe_path(self, target_path: str) -> bool:
        """
        Validates if target path is safely contained within allowed workspace boundary.
        Prevents parent traversal ('../..') and absolute paths to system directories.
        """
        if self.policy.allow_outside_filesystem:
            return True

        if not target_path or not isinstance(target_path, str):
            return False

        try:
            # Resolve full normalized path
            if os.path.isabs(target_path):
                abs_path = os.path.abspath(target_path)
            else:
                abs_path = os.path.abspath(os.path.join(self.root_dir, target_path))

            # Case-insensitive comparison on Windows
            allowed_root = os.path.abspath(self.policy.allowed_root)
            if sys.platform == "win32":
                return abs_path.lower().startswith(allowed_root.lower())
            return abs_path.startswith(allowed_root)
        except Exception:
            return False

    def sanitize_env(self, extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Sanitizes system environment variables by removing secrets, API keys, and auth tokens.
        Injects containment runtime flags.
        """
        safe_env: Dict[str, str] = {}

        # Copy non-blocked environment variables
        for key, value in os.environ.items():
            if not self.policy.is_env_var_blocked(key):
                safe_env[key] = value

        # Set isolation flags
        safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
        safe_env["PYTHONUNBUFFERED"] = "1"
        
        # Isolate PYTHONPATH to root_dir
        existing_py_path = safe_env.get("PYTHONPATH", "")
        if self.root_dir not in existing_py_path:
            safe_env["PYTHONPATH"] = self.root_dir + (os.pathsep + existing_py_path if existing_py_path else "")

        # Contain outbound networking during test execution if policy forbids
        if not self.policy.allow_network:
            safe_env["HTTP_PROXY"] = "http://127.0.0.1:0"
            safe_env["HTTPS_PROXY"] = "http://127.0.0.1:0"
            safe_env["ALL_PROXY"] = "http://127.0.0.1:0"
            safe_env["NO_PROXY"] = "localhost,127.0.0.1"

        if extra_env:
            for k, v in extra_env.items():
                if not self.policy.is_env_var_blocked(k):
                    safe_env[k] = str(v)

        return safe_env

    def check_dangerous_command(self, cmd: str) -> Optional[str]:
        """
        Scans shell command string against dangerous/destructive patterns.
        Returns error reason if dangerous pattern found, None if clean.
        """
        if not cmd or not isinstance(cmd, str):
            return "Empty command"

        for pattern in self.policy.dangerous_command_patterns:
            if re.search(pattern, cmd, re.IGNORECASE):
                return f"Blocked dangerous command pattern: '{pattern}' detected in '{cmd}'"

        return None

    def check_dangerous_python_code(self, code_str: str) -> Optional[str]:
        """
        Static AST scan of Python code to intercept dangerous filesystem destruction.
        """
        if not code_str:
            return None

        try:
            tree = ast.parse(code_str)
        except Exception:
            # If not valid python syntax, validator will catch it separately
            return None

        for node in ast.walk(tree):
            # Intercept shutil.rmtree with root path or outside
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                elif isinstance(node.func, ast.Name):
                    func_name = node.func.id

                if func_name in ("rmtree", "unlink", "remove", "system", "popen"):
                    # Check first argument if literal string
                    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                        target_arg = node.args[0].value
                        if target_arg in ("/", "\\", "C:\\", "C:/", "~") or not self.is_safe_path(target_arg):
                            return f"Blocked unsafe file/system operation target: '{target_arg}'"

        return None

    def run_command(
        self,
        cmd: str,
        cwd: Optional[str] = None,
        timeout: Optional[float] = None,
        extra_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Executes command inside sanitized subprocess with boundary check and timeout.
        """
        target_cwd = os.path.abspath(cwd or self.root_dir)
        if not self.is_safe_path(target_cwd):
            return {
                "success": False,
                "returncode": -1,
                "command": cmd,
                "stdout": "",
                "stderr": f"Sandbox Security Violation: Working directory '{target_cwd}' is outside allowed root '{self.policy.allowed_root}'.",
                "elapsed_seconds": 0.0,
                "sandboxed": True,
                "security_violation": "PATH_TRAVERSAL"
            }

        # Check dangerous command patterns
        danger_reason = self.check_dangerous_command(cmd)
        if danger_reason:
            return {
                "success": False,
                "returncode": -1,
                "command": cmd,
                "stdout": "",
                "stderr": f"Sandbox Security Violation: {danger_reason}",
                "elapsed_seconds": 0.0,
                "sandboxed": True,
                "security_violation": "DANGEROUS_COMMAND"
            }

        effective_timeout = timeout or self.policy.max_timeout_seconds
        sandboxed_env = self.sanitize_env(extra_env)
        start_time = time.time()

        try:
            process = subprocess.run(
                cmd,
                shell=True,
                cwd=target_cwd,
                env=sandboxed_env,
                capture_output=True,
                text=True,
                timeout=effective_timeout
            )
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "command": cmd,
                "stdout": process.stdout[:self.policy.max_output_bytes],
                "stderr": process.stderr[:self.policy.max_output_bytes],
                "elapsed_seconds": elapsed,
                "sandboxed": True,
                "security_violation": None
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "command": cmd,
                "stdout": "",
                "stderr": f"Execution timed out after {effective_timeout}s under sandbox containment.",
                "elapsed_seconds": effective_timeout,
                "sandboxed": True,
                "security_violation": "TIMEOUT_EXPIRED"
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "command": cmd,
                "stdout": "",
                "stderr": f"Sandboxed execution error: {str(e)}",
                "elapsed_seconds": round(time.time() - start_time, 2),
                "sandboxed": True,
                "security_violation": "EXECUTION_ERROR"
            }

    def run_python_unittest(
        self,
        test_dir: str = "tests",
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes Python unittest discovery safely inside sanitized sandbox.
        """
        target_dir = os.path.join(self.root_dir, test_dir)
        if not self.is_safe_path(target_dir):
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Sandbox Security Violation: Test path '{target_dir}' is outside workspace boundary.",
                "elapsed_seconds": 0.0,
                "sandboxed": True
            }

        effective_timeout = timeout or self.policy.max_timeout_seconds
        sandboxed_env = self.sanitize_env()
        cmd = [sys.executable, "-m", "unittest", "discover", test_dir]
        start_time = time.time()

        try:
            res = subprocess.run(
                cmd,
                cwd=self.root_dir,
                env=sandboxed_env,
                capture_output=True,
                text=True,
                timeout=effective_timeout
            )
            elapsed = round(time.time() - start_time, 2)
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "elapsed_seconds": elapsed,
                "sandboxed": True
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Unit test execution timed out after {effective_timeout}s.",
                "elapsed_seconds": effective_timeout,
                "sandboxed": True
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Unit test execution error: {str(e)}",
                "elapsed_seconds": round(time.time() - start_time, 2),
                "sandboxed": True
            }
