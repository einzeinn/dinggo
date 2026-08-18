import os
from typing import Dict, Any, Optional


def run_command(cmd: str, cwd: str = ".", timeout: Optional[float] = 120.0) -> Dict[str, Any]:
    """
    Executes a shell command inside the SandboxedRunner security boundary.
    NOTE: Confirmation MUST be solicited from the user in CLI UI prior to invoking this tool.
    """
    from core.sandbox.runner import SandboxedRunner
    abs_cwd = os.path.abspath(cwd)
    runner = SandboxedRunner(root_dir=abs_cwd)
    return runner.run_command(cmd=cmd, cwd=abs_cwd, timeout=timeout)


