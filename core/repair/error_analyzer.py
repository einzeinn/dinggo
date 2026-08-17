"""Error & Stack Trace Analyzer for Dinggo Product Factory Repair Engine."""
import re
from typing import Dict, Any, Optional
from core.testing.test_runner import TestFailure


class ErrorAnalyzer:
    """Analyzes test failures, extracting root cause, target file, and line number."""

    def analyze_failure(self, failure: TestFailure) -> Dict[str, Any]:
        """Extract diagnostic information from a test failure."""
        target_file = failure.target_file
        line_num = failure.line_number
        root_cause = failure.error_message

        # Search stack trace for File "path", line X
        if failure.stack_trace:
            file_matches = re.findall(r'File "([^"]+)", line (\d+)', failure.stack_trace)
            if file_matches:
                # Find non-unittest/library file (preferably local project file)
                for f_path, l_str in reversed(file_matches):
                    if not any(lib in f_path for lib in ("unittest", "site-packages", "lib", "Lib")):
                        target_file = f_path
                        line_num = int(l_str)
                        break

                if not target_file:
                    target_file, l_str = file_matches[-1]
                    line_num = int(l_str)

            # Extract last line of exception message
            lines = [l.strip() for l in failure.stack_trace.splitlines() if l.strip()]
            if lines:
                root_cause = lines[-1]

        return {
            "test_id": failure.test_id,
            "test_name": failure.test_name,
            "target_file": target_file,
            "line_number": line_num,
            "root_cause": root_cause,
            "error_message": failure.error_message,
            "stack_trace": failure.stack_trace
        }
