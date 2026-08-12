import subprocess
import os
import time
from typing import Dict, Any


def run_command(cmd: str, cwd: str = ".") -> Dict[str, Any]:
    """
    Executes a shell command in the specified directory.
    NOTE: Confirmation MUST be solicited from the user in CLI UI prior to invoking this tool.
    """
    abs_cwd = os.path.abspath(cwd)
    start_time = time.time()
    try:
        process = subprocess.run(
            cmd,
            shell=True,
            cwd=abs_cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        elapsed = round(time.time() - start_time, 2)
        return {
            "success": process.returncode == 0,
            "returncode": process.returncode,
            "command": cmd,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "elapsed_seconds": elapsed
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "command": cmd,
            "stdout": "",
            "stderr": "Command execution timed out after 120 seconds.",
            "elapsed_seconds": 120.0
        }
    except Exception as e:
        return {
            "success": False,
            "returncode": -1,
            "command": cmd,
            "stdout": "",
            "stderr": f"Gagal mengeksekusi command: {str(e)}",
            "elapsed_seconds": round(time.time() - start_time, 2)
        }
