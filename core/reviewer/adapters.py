"""Independent reviewer adapters for Dinggo Product Factory."""
import os
import re
import json
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type

import httpx

from core.reviewer.models import (
    ReviewReport,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
    ReviewPackage,
    ReviewLevel,
    ReviewMode,
    ContextRequest,
)
from core.spec.models import ProductSpec
from core.ollama_client import OllamaClient


AUDIT_SYSTEM_PROMPT = (
    "You are Dinggo's Independent Senior Software Auditor.\n"
    "You perform rigorous, unbiased, evidence-based code audits.\n"
    "You act like an investigator checking concrete evidence rather than making assumptions.\n\n"
    "EVALUATION CRITERIA:\n"
    "1. REQUIREMENTS VERIFICATION: Does the implementation truly satisfy the specification and acceptance criteria? Is it a stub / echo returning fake data?\n"
    "2. CODE QUALITY: Maintainability, error handling, typing, code smells, duplication.\n"
    "3. SECURITY: Authentication bypass, password handling, injection, secrets, dynamic eval.\n"
    "4. ARCHITECTURE: Decoupled design, proper layer separation.\n\n"
    "RESPONSE FORMAT (JSON ONLY):\n"
    "If you require additional imported files to verify the logic, respond with:\n"
    "{\n"
    '  "context_request": {\n'
    '    "needed_files": ["relative/path/to/helper.py"],\n'
    '    "reason": "Explain why this file is needed for verification"\n'
    "  }\n"
    "}\n\n"
    "Otherwise, respond with the final audit report:\n"
    "{\n"
    '  "auditor": "Name of auditor",\n'
    '  "score": 85.0,\n'
    '  "verdict": "approved" | "revisions_required" | "rejected",\n'
    '  "summary": "Concrete audit assessment summary",\n'
    '  "findings": [\n'
    "    {\n"
    '      "id": "FIND-001",\n'
    '      "category": "requirements" | "code_quality" | "security" | "architecture",\n'
    '      "severity": "critical" | "high" | "medium" | "low" | "info",\n'
    '      "requirement_id": "AUTH-002",\n'
    '      "file_path": "backend/auth.py",\n'
    '      "line_number": 42,\n'
    '      "title": "Short title of issue",\n'
    '      "description": "Detailed explanation of what is wrong",\n'
    '      "evidence": "Concrete code snippet or function call showing the violation",\n'
    '      "recommendation": "Actionable concrete recommendation to resolve"\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "Do NOT include explanations outside the JSON object."
)


def build_package_prompt(package: ReviewPackage) -> str:
    """Builds a targeted, scoped prompt from a ReviewPackage."""
    prompt = "## INDEPENDENT CODE AUDIT: SCOPED REVIEW PACKAGE\n\n"
    prompt += f"**Package ID:** `{package.package_id}` (Scope: `{package.level.value.upper()}`)\n"
    if package.requirement_title:
        prompt += f"**Module / Target:** {package.requirement_title}\n\n"

    if package.requirements:
        prompt += f"### Target Traceable Requirements ({len(package.requirements)}):\n"
        for req in package.requirements:
            r_title = getattr(req, "title", str(req))
            r_id = getattr(req, "id", "REQ")
            r_desc = getattr(req, "description", "")
            r_ac = getattr(req, "acceptance_criteria", [])
            prompt += f"- **[{r_id}] {r_title}**\n"
            if r_desc:
                prompt += f"  * Description: {r_desc}\n"
            if r_ac:
                prompt += f"  * Criteria: {', '.join(r_ac[:4])}\n"
        prompt += "\n"
    elif package.requirement_id:
        prompt += f"### Target Traceable Requirement: [{package.requirement_id}] {package.requirement_title or ''}\n"
        if package.requirement_description:
            prompt += f"**Description:** {package.requirement_description}\n"
        if package.acceptance_criteria:
            prompt += "**Acceptance Criteria:**\n"
            for ac in package.acceptance_criteria:
                prompt += f"- {ac}\n"
        prompt += "\n"

    prompt += f"### Target Changed Files ({len(package.target_files)}):\n"
    for tf in package.target_files:
        prompt += f"- `{tf}`\n"
    prompt += "\n"

    if package.file_contents:
        prompt += "### Implementation Source Code:\n"
        for tf, content in package.file_contents.items():
            ext = os.path.splitext(tf)[1].lstrip(".") or "text"
            prompt += f"#### File: `{tf}`\n```{ext}\n{content}\n```\n\n"

    if package.additional_context:
        prompt += "### Additional Requested Context:\n"
        for cf, content in package.additional_context.items():
            ext = os.path.splitext(cf)[1].lstrip(".") or "text"
            prompt += f"#### File: `{cf}` (Retrieved on Demand)\n```{ext}\n{content}\n```\n\n"

    if package.relevant_tests:
        prompt += f"### Relevant Tests:\n"
        for t in package.relevant_tests:
            prompt += f"- `{t}`\n"
        if package.test_results:
            prompt += f"**Test Result:** {package.test_results.get('status', 'UNKNOWN')} ({package.test_results.get('tests_passed', 0)}/{package.test_results.get('tests_total', 0)} passed)\n"
        prompt += "\n"

    if package.dependencies:
        prompt += f"### Relevant Dependencies:\n- {', '.join(package.dependencies)}\n\n"

    prompt += (
        "### Auditor Instructions:\n"
        "1. Verify if the code truly satisfies the requirements and acceptance criteria.\n"
        "2. Detect any stub, mock return, unauthenticated bypass, or dangerous logic.\n"
        "3. If you need to inspect an imported helper module, emit a `context_request`.\n"
        "4. Otherwise, provide the JSON ReviewReport with score, verdict, and concrete evidence."
    )
    return prompt


def collect_codebase_context(root_dir: str, max_chars: int = 25000) -> Dict[str, Any]:
    """Collects repository file tree and source code snippets for full audit review."""
    ignore_dirs = {
        ".git", ".venv", "venv", "env", "node_modules", "dist", "build",
        "__pycache__", ".dinggo", ".pytest_cache", ".idea", ".vscode", ".context"
    }
    file_list = []
    file_contents = {}
    current_chars = 0

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
        for file in files:
            if file.startswith("."):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
            file_list.append(rel_path)

            if file.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".yaml", ".yml", ".json", ".html", ".css", ".md")):
                if current_chars < max_chars:
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                            content = fp.read()
                            if len(content) > 5000:
                                content = content[:5000] + "\n... [truncated]"
                            file_contents[rel_path] = content
                            current_chars += len(content)
                    except Exception:
                        pass

    return {
        "tree": file_list,
        "files": file_contents
    }


def build_audit_prompt(root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None, max_chars: int = 25000) -> str:
    """Builds structured independent review prompt supporting both ReviewPackage and full repository context."""
    if package:
        return build_package_prompt(package)

    code_ctx = collect_codebase_context(root_dir, max_chars=max_chars)
    
    prompt = "## INDEPENDENT CODE AUDIT REQUEST (FULL REPOSITORY)\n\n"
    if spec:
        prompt += f"### Specification Context\n"
        prompt += f"- Project Name: {spec.name}\n"
        prompt += f"- Summary: {spec.summary}\n"
        if spec.architecture:
            arch_info = []
            if getattr(spec.architecture, "framework", None):
                arch_info.append(f"Framework: {spec.architecture.framework}")
            if getattr(spec.architecture, "runtime", None):
                arch_info.append(f"Runtime: {spec.architecture.runtime}")
            if getattr(spec.architecture, "database", None):
                arch_info.append(f"Database: {spec.architecture.database}")
            if arch_info:
                prompt += f"- Architecture: {', '.join(arch_info)}\n"
        if spec.requirements:
            prompt += "- Key Requirements:\n"
            for req in spec.requirements[:15]:
                prompt += f"  * [{req.id}] {req.title} ({req.priority.value if hasattr(req.priority, 'value') else req.priority}): {req.description}\n"
        prompt += "\n"

    prompt += f"### Repository Structure ({len(code_ctx['tree'])} files)\n"
    prompt += "```text\n"
    prompt += "\n".join(code_ctx["tree"][:40])
    if len(code_ctx["tree"]) > 40:
        prompt += f"\n... (+{len(code_ctx['tree']) - 40} more files)"
    prompt += "\n```\n\n"

    prompt += "### Codebase Source Files\n"
    for path, content in code_ctx["files"].items():
        ext = os.path.splitext(path)[1].lstrip(".") or "text"
        prompt += f"#### File: `{path}`\n```{ext}\n{content}\n```\n\n"

    prompt += (
        "Please conduct a comprehensive 4-quadrant audit (Requirements, Code Quality, Security, Architecture).\n"
        "Output ONLY the JSON object conforming to ReviewReport schema."
    )
    return prompt


def parse_review_response(response_text: str, default_auditor: str = "Dinggo Independent Auditor") -> ReviewReport:
    """Robustly extracts and validates JSON audit reports from LLM responses with ContextRequest support."""
    text = response_text.strip()
    data: Dict[str, Any] = {}

    # Check if input is a CLI wrapper JSON, e.g. {"status": "SUCCESS", "response": "..."}
    try:
        raw_obj = json.loads(text)
        if isinstance(raw_obj, dict):
            if "response" in raw_obj and isinstance(raw_obj["response"], str) and not raw_obj.get("findings"):
                text = raw_obj["response"].strip()
            else:
                data = raw_obj
    except Exception:
        pass

    if not data:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            inner_text = match.group(1).strip()
        else:
            inner_text = text

        if not (inner_text.startswith("{") and inner_text.endswith("}")):
            start = inner_text.find("{")
            end = inner_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                inner_text = inner_text[start:end+1]

        try:
            data = json.loads(inner_text)
        except Exception:
            data = {}

    auditor = data.get("auditor") or default_auditor

    # 1. Check for Context Request
    context_requests: List[ContextRequest] = []
    if "context_request" in data and isinstance(data["context_request"], dict):
        cr = data["context_request"]
        needed = cr.get("needed_files", [])
        if isinstance(needed, list) and needed:
            req_obj = ContextRequest(needed_files=needed, reason=str(cr.get("reason", "Investigative verification")))
            context_requests.append(req_obj)
            return ReviewReport(
                auditor=auditor,
                score=50.0,
                verdict="revisions_required",
                summary=f"Context requested: {', '.join(needed)} ({req_obj.reason})",
                findings=[],
                context_requests=context_requests,
                raw_response=response_text
            )

    # 2. Parse findings
    raw_findings = data.get("findings") if isinstance(data.get("findings"), list) else []
    parsed_findings: List[ReviewFinding] = []

    for idx, rf in enumerate(raw_findings, start=1):
        if not isinstance(rf, dict):
            continue
        
        cat_str = str(rf.get("category", "")).lower().strip()
        if "req" in cat_str:
            cat = ReviewCategory.REQUIREMENTS
        elif "sec" in cat_str:
            cat = ReviewCategory.SECURITY
        elif "arch" in cat_str:
            cat = ReviewCategory.ARCHITECTURE
        else:
            cat = ReviewCategory.CODE_QUALITY

        sev_str = str(rf.get("severity", "")).lower().strip()
        if "crit" in sev_str:
            sev = ReviewSeverity.CRITICAL
        elif "high" in sev_str or "err" in sev_str:
            sev = ReviewSeverity.HIGH
        elif "med" in sev_str or "warn" in sev_str:
            sev = ReviewSeverity.MEDIUM
        elif "low" in sev_str:
            sev = ReviewSeverity.LOW
        else:
            sev = ReviewSeverity.INFO

        fid = rf.get("id") or f"FIND-{idx:03d}"
        title = str(rf.get("title") or rf.get("issue") or f"Audit Finding {idx}").strip()
        desc = str(rf.get("description") or rf.get("details") or title).strip()
        rec = str(rf.get("recommendation") or rf.get("fix") or "Review and address finding.").strip()
        ev = rf.get("evidence") or rf.get("proof") or rf.get("snippet")
        req_id = rf.get("requirement_id") or rf.get("req_id")
        fpath = rf.get("file_path") or rf.get("file")
        lno = rf.get("line_number") or rf.get("line")
        try:
            lno = int(lno) if lno is not None else None
        except (ValueError, TypeError):
            lno = None

        parsed_findings.append(ReviewFinding(
            id=fid,
            category=cat,
            severity=sev,
            requirement_id=str(req_id) if req_id else None,
            file_path=str(fpath) if fpath else None,
            line_number=lno,
            title=title,
            description=desc,
            evidence=str(ev) if ev else None,
            recommendation=rec
        ))

    # Fallback: Parse markdown structured findings if LLM did not return JSON findings list
    if not parsed_findings and ("###" in text or "####" in text or "**Issue:" in text or "**Fix:" in text or "Findings" in text):
        md_sections = re.split(r"(?=####?\s+)", text)
        f_idx = 1
        for sec in md_sections:
            sec = sec.strip()
            if not sec or sec.startswith("## ") or sec.startswith("### Recommended") or sec.startswith("### Key Findings") or sec.startswith("### Solutions"):
                continue

            lines = sec.splitlines()
            title_line = lines[0].lstrip("#").strip() if lines else ""
            if not title_line:
                continue

            cat = ReviewCategory.CODE_QUALITY
            lower_sec = sec.lower()
            if "security" in lower_sec:
                cat = ReviewCategory.SECURITY
            elif "requirement" in lower_sec:
                cat = ReviewCategory.REQUIREMENTS
            elif "architecture" in lower_sec:
                cat = ReviewCategory.ARCHITECTURE

            sev = ReviewSeverity.MEDIUM
            if "critical" in lower_sec or "rce" in lower_sec or "injection" in lower_sec or "eval(" in lower_sec:
                sev = ReviewSeverity.CRITICAL
            elif "high" in lower_sec or "dangerous" in lower_sec or "vulnerability" in lower_sec:
                sev = ReviewSeverity.HIGH
            elif "low" in lower_sec or "minor" in lower_sec or "overhead" in lower_sec:
                sev = ReviewSeverity.LOW

            issue_match = re.search(r"\*\*(?:Issue|Problem|Description):\*\*\s*([^\n*]+)", sec, re.IGNORECASE)
            fix_match = re.search(r"\*\*(?:Fix|Recommendation|Solution):\*\*\s*([^\n*]+)", sec, re.IGNORECASE)
            evidence_match = re.search(r"\*\*(?:Evidence|Snippet|Code):\*\*\s*([^\n*]+)", sec, re.IGNORECASE)

            desc = issue_match.group(1).strip() if issue_match else sec[:200]
            rec = fix_match.group(1).strip() if fix_match else "Review code according to findings."
            ev = evidence_match.group(1).strip() if evidence_match else None

            parsed_findings.append(ReviewFinding(
                id=f"FIND-{f_idx:03d}",
                category=cat,
                severity=sev,
                file_path=None,
                line_number=None,
                title=title_line,
                description=desc,
                evidence=ev,
                recommendation=rec
            ))
            f_idx += 1

    # Calculate or normalize score
    score = data.get("score")
    if score is not None:
        try:
            score = float(score)
            score = max(0.0, min(100.0, score))
        except (ValueError, TypeError):
            score = None

    if score is None:
        score = 100.0
        for f in parsed_findings:
            if f.severity == ReviewSeverity.CRITICAL:
                score -= 30.0
            elif f.severity == ReviewSeverity.HIGH:
                score -= 15.0
            elif f.severity == ReviewSeverity.MEDIUM:
                score -= 5.0
            elif f.severity == ReviewSeverity.LOW:
                score -= 2.0
        score = max(0.0, score)

    # Determine verdict
    raw_verdict = str(data.get("verdict", "")).lower().strip()
    if raw_verdict in ("approved", "revisions_required", "rejected"):
        verdict = raw_verdict
    else:
        if score >= 90.0 and not any(f.severity in (ReviewSeverity.CRITICAL, ReviewSeverity.HIGH) for f in parsed_findings):
            verdict = "approved"
        elif score >= 70.0:
            verdict = "revisions_required"
        else:
            verdict = "rejected"

    summary = data.get("summary") or f"Audit complete. Score: {score:.1f}/100. Verdict: {verdict.upper()} ({len(parsed_findings)} findings)."

    return ReviewReport(
        auditor=auditor,
        score=score,
        verdict=verdict,
        findings=parsed_findings,
        summary=summary,
        context_requests=context_requests,
        raw_response=response_text
    )


class BaseReviewerAdapter(ABC):
    """Abstract interface for independent code audit adapters."""

    name: str = "Base Reviewer"
    provider_id: str = "base"

    @abstractmethod
    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        """Performs an independent audit of the codebase or targeted ReviewPackage."""
        pass


class MockReviewerAdapter(BaseReviewerAdapter):
    """Deterministic static-analysis auditor for fast, reproducible, offline evaluation."""

    name: str = "Dinggo Heuristic Auditor"
    provider_id: str = "mock"

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        findings: List[ReviewFinding] = []
        f_count = 1

        # Scan target files from package if provided, else scan root directory
        files_to_scan = []
        if package and package.target_files:
            files_to_scan = [os.path.join(root_dir, tf) for tf in package.target_files if os.path.isfile(os.path.join(root_dir, tf))]
        else:
            for root, dirs, files in os.walk(root_dir):
                dirs[:] = [d for d in dirs if d not in (".git", ".venv", "dist", "node_modules", "__pycache__", ".dinggo")]
                for file in files:
                    if file.endswith((".py", ".js", ".ts", ".tsx", ".yaml", ".json")):
                        files_to_scan.append(os.path.join(root, file))

        for file_path in files_to_scan:
            rel_path = os.path.relpath(file_path, root_dir).replace("\\", "/")
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
                                requirement_id=package.requirement_id if package else None,
                                file_path=rel_path,
                                line_number=line_idx,
                                title="Hardcoded credential pattern detected",
                                description=f"Potential hardcoded secret assigned in {rel_path}:{line_idx}",
                                evidence=line.strip(),
                                recommendation="Extract sensitive values into environment variables or secrets manager."
                            ))
                            f_count += 1

                        # 2. Security Check: Dangerous execution
                        if "eval(" in line or "exec(" in line:
                            findings.append(ReviewFinding(
                                id=f"FIND-{f_count:03d}",
                                category=ReviewCategory.SECURITY,
                                severity=ReviewSeverity.CRITICAL,
                                requirement_id=package.requirement_id if package else None,
                                file_path=rel_path,
                                line_number=line_idx,
                                title="Dangerous dynamic evaluation",
                                description=f"Use of eval/exec detected in {rel_path}:{line_idx}",
                                evidence=line.strip(),
                                recommendation="Refactor to avoid dynamic code evaluation."
                            ))
                            f_count += 1

                        # 3. Code Quality Check: bare except
                        if line.strip() == "except:":
                            findings.append(ReviewFinding(
                                id=f"FIND-{f_count:03d}",
                                category=ReviewCategory.CODE_QUALITY,
                                severity=ReviewSeverity.MEDIUM,
                                requirement_id=package.requirement_id if package else None,
                                file_path=rel_path,
                                line_number=line_idx,
                                title="Bare except clause",
                                description=f"Catch-all bare except used in {rel_path}:{line_idx}",
                                evidence=line.strip(),
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
            auditor=self.name,
            score=score,
            verdict=verdict,
            findings=findings,
            summary=summary
        )


class OllamaReviewerAdapter(BaseReviewerAdapter):
    """Auditor powered by Local Ollama Models."""

    name: str = "Ollama Local Auditor"
    provider_id: str = "ollama"

    def __init__(
        self,
        ollama_client: Optional[OllamaClient] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.client = ollama_client or OllamaClient(base_url=base_url)
        self.model = model or os.getenv("MODEL_REVIEWER") or os.getenv("MODEL_CODEGEN") or "qwen2.5:3b"

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        if not self.client.is_available():
            mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
            mock_rep.auditor = f"{self.name} (Offline Fallback - Heuristic)"
            mock_rep.summary = f"[Ollama server unavailable at {self.client.base_url}] " + mock_rep.summary
            return mock_rep

        prompt = build_audit_prompt(root_dir, spec=spec, package=package)
        res = self.client.generate(
            model=self.model,
            prompt=prompt,
            system_prompt=AUDIT_SYSTEM_PROMPT,
            json_format=True,
            temperature=0.1
        )

        if not res.get("success"):
            err_msg = res.get("error", "Unknown generation failure")
            mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
            mock_rep.auditor = f"{self.name} (Error Fallback)"
            mock_rep.summary = f"[Ollama Error: {err_msg}] " + mock_rep.summary
            return mock_rep

        resolved_model = self.client.resolve_model_name(self.model)
        auditor_label = f"Ollama Auditor ({resolved_model})"
        return parse_review_response(res.get("response", ""), default_auditor=auditor_label)


class CodexReviewerAdapter(BaseReviewerAdapter):
    """Auditor powered by OpenAI / Codex CLI."""

    name: str = "Codex CLI Auditor"
    provider_id: str = "codex"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        cli_path: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("CODEX_MODEL", "gpt-4o")
        self.cli_path = cli_path or shutil.which("codex") or shutil.which("codex.cmd")

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        prompt = build_audit_prompt(root_dir, spec=spec, package=package)

        # 1. If API key available, execute via OpenAI REST API
        if self.api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                    resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return parse_review_response(content, default_auditor=f"Codex / OpenAI ({self.model})")
                    else:
                        error_detail = resp.text
            except Exception as e:
                error_detail = str(e)
        else:
            error_detail = "No OPENAI_API_KEY or CODEX_API_KEY configured"

        # 2. If CLI executable is available, execute via CLI subprocess with stdin
        if self.cli_path:
            try:
                cmd = [self.cli_path, "exec", "--skip-git-repo-check", "-"]
                proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, cwd=root_dir)
                if proc.returncode == 0 and proc.stdout:
                    return parse_review_response(proc.stdout, default_auditor=f"Codex CLI ({os.path.basename(self.cli_path)})")
                else:
                    error_detail += f" | CLI return code {proc.returncode}: {proc.stderr[:200]}"
            except Exception as e:
                error_detail += f" | CLI execution error: {str(e)}"

        # 3. Graceful fallback
        mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
        mock_rep.auditor = f"{self.name} (Fallback - Heuristic)"
        mock_rep.summary = f"[{error_detail}] " + mock_rep.summary
        return mock_rep


class ClaudeReviewerAdapter(BaseReviewerAdapter):
    """Auditor powered by Anthropic Claude Code CLI / API."""

    name: str = "Claude Code CLI Auditor"
    provider_id: str = "claude"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cli_path: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-7-sonnet-20250219")
        self.cli_path = cli_path or shutil.which("claude") or shutil.which("claude.cmd") or shutil.which("claude-code")

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        prompt = build_audit_prompt(root_dir, spec=spec, package=package)

        # 1. If API key available, execute via Anthropic Messages REST API
        if self.api_key:
            try:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "system": AUDIT_SYSTEM_PROMPT,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1
                }
                with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                    resp = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        content_blocks = data.get("content", [])
                        text_resp = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
                        return parse_review_response(text_resp, default_auditor=f"Claude Code ({self.model})")
                    else:
                        error_detail = resp.text
            except Exception as e:
                error_detail = str(e)
        else:
            error_detail = "No ANTHROPIC_API_KEY or CLAUDE_API_KEY configured"

        # 2. If CLI executable available, run Claude CLI with stdin
        if self.cli_path:
            try:
                cmd = [self.cli_path, "-p", "-", "--output-format", "json"]
                proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, cwd=root_dir)
                if proc.returncode == 0 and proc.stdout:
                    return parse_review_response(proc.stdout, default_auditor=f"Claude Code CLI ({os.path.basename(self.cli_path)})")
                else:
                    error_detail += f" | CLI code {proc.returncode}: {proc.stderr[:200]}"
            except Exception as e:
                error_detail += f" | CLI execution error: {str(e)}"

        # 3. Graceful fallback
        mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
        mock_rep.auditor = f"{self.name} (Fallback - Heuristic)"
        mock_rep.summary = f"[{error_detail}] " + mock_rep.summary
        return mock_rep


class AgyReviewerAdapter(BaseReviewerAdapter):
    """Auditor powered by Antigravity (AGY) / Gemini API / CLI."""

    name: str = "Antigravity (AGY) CLI Auditor"
    provider_id: str = "agy"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        cli_path: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.cli_path = cli_path or shutil.which("agy") or shutil.which("agy.cmd") or shutil.which("antigravity")

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        prompt = build_audit_prompt(root_dir, spec=spec, package=package)

        # 1. If API key available, execute via Google Gemini REST API
        if self.api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
                payload = {
                    "systemInstruction": {
                        "parts": [{"text": AUDIT_SYSTEM_PROMPT}]
                    },
                    "contents": [
                        {"parts": [{"text": prompt}]}
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1
                    }
                }
                with httpx.Client(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        text_resp = ""
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_resp = "".join(p.get("text", "") for p in parts)
                        return parse_review_response(text_resp, default_auditor=f"Antigravity / Gemini ({self.model})")
                    else:
                        error_detail = resp.text
            except Exception as e:
                error_detail = str(e)
        else:
            error_detail = "No GEMINI_API_KEY configured"

        # 2. If CLI executable available, run AGY CLI with stdin
        if self.cli_path:
            try:
                cmd = [self.cli_path, "--print", "-", "--output-format", "json"]
                proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30, cwd=root_dir)
                if proc.returncode == 0 and proc.stdout:
                    return parse_review_response(proc.stdout, default_auditor=f"Antigravity CLI ({os.path.basename(self.cli_path)})")
                else:
                    error_detail += f" | CLI code {proc.returncode}: {proc.stderr[:200]}"
            except Exception as e:
                error_detail += f" | CLI execution error: {str(e)}"

        # 3. Graceful fallback
        mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
        mock_rep.auditor = f"{self.name} (Fallback - Heuristic)"
        mock_rep.summary = f"[{error_detail}] " + mock_rep.summary
        return mock_rep


class OpenAICompatibleReviewerAdapter(BaseReviewerAdapter):
    """Universal auditor for OpenAI-compatible REST endpoints (e.g. Groq, LiteLLM, vLLM, LM Studio)."""

    name: str = "OpenAI-Compatible Custom Auditor"
    provider_id: str = "openai_compatible"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("OPENAI_COMPATIBLE_BASE_URL", "http://localhost:8000/v1")).rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_COMPATIBLE_API_KEY", "dummy-key")
        self.model = model or os.getenv("OPENAI_COMPATIBLE_MODEL", "default")

    def audit(self, root_dir: str, spec: Optional[ProductSpec] = None, package: Optional[ReviewPackage] = None) -> ReviewReport:
        prompt = build_audit_prompt(root_dir, spec=spec, package=package)
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": AUDIT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return parse_review_response(content, default_auditor=f"Custom Auditor ({self.model})")
                else:
                    error_detail = resp.text
        except Exception as e:
            error_detail = str(e)

        mock_rep = MockReviewerAdapter().audit(root_dir, spec, package=package)
        mock_rep.auditor = f"{self.name} (Fallback - Heuristic)"
        mock_rep.summary = f"[{error_detail}] " + mock_rep.summary
        return mock_rep


# =====================================================================
# Provider Registry & Provider Resolver
# =====================================================================

class ProviderRegistry:
    """Registry maintaining registered Reviewer Adapters."""

    _adapters: Dict[str, Type[BaseReviewerAdapter]] = {
        "codex": CodexReviewerAdapter,
        "agy": AgyReviewerAdapter,
        "claude": ClaudeReviewerAdapter,
        "ollama": OllamaReviewerAdapter,
        "openai_compatible": OpenAICompatibleReviewerAdapter,
        "mock": MockReviewerAdapter,
    }

    @classmethod
    def register(cls, provider_id: str, adapter_cls: Type[BaseReviewerAdapter]) -> None:
        """Register a new reviewer adapter class."""
        cls._adapters[provider_id.lower().strip()] = adapter_cls

    @classmethod
    def get(cls, provider_id: str) -> Optional[Type[BaseReviewerAdapter]]:
        """Get reviewer adapter class by ID."""
        return cls._adapters.get(provider_id.lower().strip())

    @classmethod
    def all(cls) -> Dict[str, Type[BaseReviewerAdapter]]:
        """Return all registered adapters."""
        return dict(cls._adapters)


class ProviderResolver:
    """Resolves best available or requested reviewer adapter based on environment & config."""

    @classmethod
    def list_available(cls, root_dir: str = ".") -> List[Dict[str, Any]]:
        """List all currently detected reviewer adapters."""
        from core.detector import ProjectDetector
        detector = ProjectDetector(root_dir)
        providers = detector.detect_providers()

        reviewers = []
        if providers.get("codex", {}).get("available"):
            reviewers.append({
                "id": "codex",
                "name": CodexReviewerAdapter.name,
                "adapter_cls": CodexReviewerAdapter,
                "details": providers["codex"].get("path") or "API / CLI ready"
            })
        if providers.get("agy", {}).get("available"):
            reviewers.append({
                "id": "agy",
                "name": AgyReviewerAdapter.name,
                "adapter_cls": AgyReviewerAdapter,
                "details": providers["agy"].get("path") or "API / CLI ready"
            })
        if providers.get("claude", {}).get("available"):
            reviewers.append({
                "id": "claude",
                "name": ClaudeReviewerAdapter.name,
                "adapter_cls": ClaudeReviewerAdapter,
                "details": providers["claude"].get("path") or "API / CLI ready"
            })
        if providers.get("ollama", {}).get("available"):
            models = providers["ollama"].get("models", [])
            models_info = f"Models: {', '.join(models[:2])}" if models else "Local Server Ready"
            reviewers.append({
                "id": "ollama",
                "name": OllamaReviewerAdapter.name,
                "adapter_cls": OllamaReviewerAdapter,
                "details": models_info
            })

        # Always provide deterministic heuristic auditor
        reviewers.append({
            "id": "mock",
            "name": MockReviewerAdapter.name,
            "adapter_cls": MockReviewerAdapter,
            "details": "Offline Static Heuristic Scanner"
        })
        return reviewers

    @classmethod
    def resolve_adapter(cls, name: Optional[str] = None, root_dir: str = ".") -> BaseReviewerAdapter:
        """Instantiate the requested or best available reviewer adapter."""
        if os.getenv("DINGGO_TEST_MODE") == "1" and not name:
            return MockReviewerAdapter()

        available = cls.list_available(root_dir)

        # 1. Explicit name requested
        if name:
            target_id = name.lower().strip()
            adapter_cls = ProviderRegistry.get(target_id)
            if adapter_cls:
                return adapter_cls()

            for r in available:
                if r["id"] == target_id:
                    return r["adapter_cls"]()

        # 2. Check dinggo.yaml config if present
        cfg_file = os.path.join(root_dir, "dinggo.yaml")
        if os.path.isfile(cfg_file):
            try:
                import yaml
                with open(cfg_file, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}
                configured_def = cfg.get("review", {}).get("default_provider")
                if configured_def:
                    adapter_cls = ProviderRegistry.get(configured_def)
                    if adapter_cls:
                        return adapter_cls()
            except Exception:
                pass

        # 3. Default to first available external adapter, else heuristic
        return available[0]["adapter_cls"]()


def get_available_reviewers(root_dir: str = ".") -> List[Dict[str, Any]]:
    """List all currently detected reviewer adapters."""
    return ProviderResolver.list_available(root_dir)


def get_reviewer_adapter(name: Optional[str] = None, root_dir: str = ".") -> BaseReviewerAdapter:
    """Instantiate the requested or best available reviewer adapter."""
    return ProviderResolver.resolve_adapter(name=name, root_dir=root_dir)
