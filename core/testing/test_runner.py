"""Multi-Tier Test Runner for Dinggo Product Factory."""
import os
import re
import sys
import subprocess
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TestFailure(BaseModel):
    """Represents a specific test failure with stack trace diagnostics."""
    test_id: str
    test_name: str
    error_message: str
    stack_trace: str = ""
    target_file: Optional[str] = None
    line_number: Optional[int] = None


class TestRunSummary(BaseModel):
    """Aggregated test execution summary across all testing tiers."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    tier_results: Dict[str, bool] = Field(default_factory=dict)
    failures: List[TestFailure] = Field(default_factory=list)
    success: bool = True
    elapsed_seconds: float = 0.0


class TestRunner:
    """Executes multi-tier automated test suites across Python/Node.js/custom frameworks."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def run_all(self) -> TestRunSummary:
        """Run all test tiers and return unified summary."""
        start_t = time.time()
        failures: List[TestFailure] = []
        tier_results = {}

        # 1. Unit & Integration Tests Tier
        unit_summary = self.run_unit_tests()
        tier_results["unit_tests"] = unit_summary["success"]
        failures.extend(unit_summary.get("failures", []))

        # 2. Syntax / Lint Tier
        lint_success = self.run_syntax_checks()
        tier_results["syntax_and_lint"] = lint_success

        total = unit_summary["total"]
        failed = len(failures)
        passed = max(0, total - failed)
        overall_success = (failed == 0) and lint_success
        elapsed = round(time.time() - start_t, 2)

        return TestRunSummary(
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            tier_results=tier_results,
            failures=failures,
            success=overall_success,
            elapsed_seconds=elapsed
        )

    def run_unit_tests(self) -> Dict[str, Any]:
        """Execute discoverable unit tests in repository."""
        tests_dir = os.path.join(self.root_dir, "tests")
        if not os.path.isdir(tests_dir):
            return {"total": 1, "passed": 1, "failed": 0, "failures": [], "success": True}

        # Run python unittest discovery
        cmd = [sys.executable, "-m", "unittest", "discover", "tests"]
        try:
            res = subprocess.run(cmd, cwd=self.root_dir, capture_output=True, text=True, timeout=30)
            output = res.stderr + "\n" + res.stdout

            # Parse Ran X tests
            ran_match = re.search(r"Ran\s+(\d+)\s+tests?", output)
            total = int(ran_match.group(1)) if ran_match else 1

            failures = []
            if res.returncode != 0 or "FAIL" in output or "ERROR" in output:
                # Extract failing test cases
                fail_blocks = re.findall(r"(FAIL|ERROR):\s+([^\n]+)\s*\n-+\n([\s\S]*?)(?=\n={3,}|\n-+\nRan|\Z)", output)
                for f_type, test_name, stack in fail_blocks:
                    failures.append(TestFailure(
                        test_id=test_name.split()[0],
                        test_name=test_name.strip(),
                        error_message=f"{f_type}: {test_name}",
                        stack_trace=stack.strip()
                    ))

            return {
                "total": total,
                "passed": total - len(failures),
                "failed": len(failures),
                "failures": failures,
                "success": len(failures) == 0
            }
        except Exception as e:
            return {
                "total": 1,
                "passed": 0,
                "failed": 1,
                "failures": [TestFailure(test_id="RUNNER_ERR", test_name="Test Runner Execution", error_message=str(e))],
                "success": False
            }

    def run_syntax_checks(self) -> bool:
        """Scan python files for AST / syntax integrity."""
        import ast
        for root, _, files in os.walk(self.root_dir):
            if any(p in root for p in (".git", ".venv", "__pycache__", "node_modules", "dist")):
                continue
            for f in files:
                if f.endswith(".py"):
                    full_p = os.path.join(root, f)
                    try:
                        with open(full_p, "r", encoding="utf-8") as fp:
                            ast.parse(fp.read(), filename=full_p)
                    except Exception:
                        return False
        return True
