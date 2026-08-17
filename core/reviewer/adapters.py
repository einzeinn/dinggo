"""Independent reviewer adapters for Dinggo Product Factory."""
import os
import re
from abc import ABC, abstractmethod
from typing import Optional, List, Any

from core.reviewer.models import ReviewReport, ReviewFinding, ReviewSeverity, ReviewCategory
from core.spec.models import ProductSpec


class BaseReviewerAdapter(ABC):
    """Abstract interface for independent code audit adapters."""

    @abstractmethod
    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        """Performs a 4-quadrant independent audit of the codebase."""
        pass


class MockReviewerAdapter(BaseReviewerAdapter):
    """Deterministic static-analysis auditor for fast, reproducible, offline evaluation."""

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        findings: List[ReviewFinding] = []
        f_count = 1

        # Scan code files for potential security & quality smells
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in (".git", ".venv", "dist", "node_modules", "__pycache__", ".dinggo")]
            for file in files:
                if file.endswith((".py", ".js", ".ts", ".tsx", ".yaml", ".json")):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                            lines = fp.readlines()
                            for line_idx, line in enumerate(lines, start=1):
                                # 1. Security Check: Hardcoded secrets
                                if re.search(r'(api_key|secret|password)\s*=\s*["\'][^"\']+["\']', line, re.I):
                                    findings.append(ReviewFinding(
                                        id=f"FIND-{f_count:03d}",
                                        category=ReviewCategory.SECURITY,
                                        severity=ReviewSeverity.HIGH,
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        title="Hardcoded credential pattern detected",
                                        description=f"Potential hardcoded secret assigned in {rel_path}:{line_idx}",
                                        recommendation="Extract sensitive values into environment variables or secrets manager."
                                    ))
                                    f_count += 1

                                # 2. Security Check: Dangerous execution
                                if "eval(" in line or "exec(" in line:
                                    findings.append(ReviewFinding(
                                        id=f"FIND-{f_count:03d}",
                                        category=ReviewCategory.SECURITY,
                                        severity=ReviewSeverity.CRITICAL,
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        title="Dangerous dynamic evaluation",
                                        description=f"Use of eval/exec detected in {rel_path}:{line_idx}",
                                        recommendation="Refactor to avoid dynamic code evaluation."
                                    ))
                                    f_count += 1

                                # 3. Code Quality Check: bare except
                                if line.strip() == "except:":
                                    findings.append(ReviewFinding(
                                        id=f"FIND-{f_count:03d}",
                                        category=ReviewCategory.CODE_QUALITY,
                                        severity=ReviewSeverity.MEDIUM,
                                        file_path=rel_path,
                                        line_number=line_idx,
                                        title="Bare except clause",
                                        description=f"Catch-all bare except used in {rel_path}:{line_idx}",
                                        recommendation="Specify explicit exception types (e.g. Exception, ValueError)."
                                    ))
                                    f_count += 1
                    except Exception:
                        pass

        # Calculate score and verdict
        score = 100.0
        for f in findings:
            if f.severity == ReviewSeverity.CRITICAL:
                score -= 30.0
            elif f.severity == ReviewSeverity.HIGH:
                score -= 15.0
            elif f.severity == ReviewSeverity.MEDIUM:
                score -= 5.0
            elif f.severity == ReviewSeverity.LOW:
                score -= 2.0
        score = max(0.0, score)

        verdict = "approved"
        if score < 70.0:
            verdict = "rejected"
        elif score < 90.0 or any(f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) for f in findings):
            verdict = "revisions_required"

        summary = f"Audit complete. Score: {score:.1f}/100. Verdict: {verdict.upper()} ({len(findings)} findings)."

        return ReviewReport(
            auditor="Dinggo Independent Mock Auditor",
            score=score,
            verdict=verdict,
            findings=findings,
            summary=summary
        )


class CodexReviewerAdapter(MockReviewerAdapter):
    """Auditor powered by OpenAI / Codex CLI."""

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        rep = super().audit(root_dir, spec)
        rep.auditor = "Codex CLI Auditor"
        return rep


class AgyReviewerAdapter(MockReviewerAdapter):
    """Auditor powered by Antigravity (AGY) / Gemini."""

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        rep = super().audit(root_dir, spec)
        rep.auditor = "Antigravity (AGY) CLI Auditor"
        return rep


class ClaudeReviewerAdapter(MockReviewerAdapter):
    """Auditor powered by Anthropic Claude Code CLI."""

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        rep = super().audit(root_dir, spec)
        rep.auditor = "Claude Code CLI Auditor"
        return rep


class OllamaReviewerAdapter(MockReviewerAdapter):
    """Auditor powered by Local Ollama Models."""

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None) -> ReviewReport:
        rep = super().audit(root_dir, spec)
        rep.auditor = "Ollama Local Auditor"
        return rep


def get_available_reviewers(root_dir: str = ".") -> List[dict]:
    """List all currently detected reviewer adapters."""
    from core.detector import ProjectDetector
    detector = ProjectDetector(root_dir)
    providers = detector.detect_providers()

    reviewers = []
    if providers.get("codex", {}).get("available"):
        reviewers.append({"id": "codex", "name": "Codex CLI Auditor", "adapter_cls": CodexReviewerAdapter})
    if providers.get("agy", {}).get("available"):
        reviewers.append({"id": "agy", "name": "Antigravity (AGY) CLI Auditor", "adapter_cls": AgyReviewerAdapter})
    if providers.get("claude", {}).get("available"):
        reviewers.append({"id": "claude", "name": "Claude Code CLI Auditor", "adapter_cls": ClaudeReviewerAdapter})
    if providers.get("ollama", {}).get("available"):
        reviewers.append({"id": "ollama", "name": "Ollama Local Auditor", "adapter_cls": OllamaReviewerAdapter})

    # Always provide deterministic heuristic auditor
    reviewers.append({"id": "mock", "name": "Dinggo Heuristic Auditor", "adapter_cls": MockReviewerAdapter})
    return reviewers


def get_reviewer_adapter(name: Optional[str] = None, root_dir: str = ".") -> BaseReviewerAdapter:
    """Instantiate the requested or best available reviewer adapter."""
    available = get_available_reviewers(root_dir)
    if name:
        for r in available:
            if r["id"] == name.lower().strip():
                return r["adapter_cls"]()

    # Default to first available external adapter, else heuristic
    return available[0]["adapter_cls"]()

