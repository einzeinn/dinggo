# RFC-010: Independent Reviewer Adapter & Review-Repair Loop

## Status
**Proposed & Accepted**

## 1. Summary
RFC-010 defines the architecture for Dinggo's **Independent Reviewer Engine** and automated **Review-Repair Loop**.
To avoid self-evaluation bias, Dinggo uses an independent auditor model (Codex, Claude, or a dedicated local auditor) to evaluate the generated codebase across four audit dimensions:
1. **Requirements Audit**
2. **Code Quality & Maintainability**
3. **Security Audit**
4. **Architecture Compliance**

---

## 2. Review Data Schema (`core/reviewer/models.py`)

```python
class ReviewSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class ReviewCategory(str, Enum):
    REQUIREMENTS = "requirements"
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    ARCHITECTURE = "architecture"

class ReviewFinding(BaseModel):
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    title: str
    description: str
    recommendation: str

class ReviewReport(BaseModel):
    auditor: str
    score: float  # 0.0 to 100.0
    verdict: Literal["approved", "revisions_required", "rejected"]
    findings: List[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    timestamp: str = Field(...)
```

---

## 3. Four-Quadrant Audit Architecture

```text
                  AUDITED CODEBASE + SPEC
                             │
                             ▼
                 INDEPENDENT AUDITOR ADAPTER
                             │
       ┌──────────────┬──────┴───────┬──────────────┐
       ▼              ▼              ▼              ▼
  Requirements   Code Quality     Security     Architecture
     Audit          Audit          Audit          Audit
       │              │              │              │
       └──────────────┴──────┬───────┴──────────────┘
                             ▼
                       REVIEW REPORT
```

---

## 4. Automated Review-Repair Loop (`core/reviewer/review_engine.py`)

When the reviewer produces findings with severity `critical` or `high`:
1. The **ReviewEngine** translates findings into targeted repair tasks.
2. Patches are applied to the codebase.
3. Automated test suite (`TestRunner`) is re-executed to guarantee no regression.
4. The codebase is re-audited up to `max_review_cycles` (default 3).

---

## 5. Review TUI Dashboard (`cli/review_view.py`)

Interactive card displaying score, verdict, and findings breakdown:

```text
╭──────────────────────────────────────────╮
│       INDEPENDENT CODE AUDIT REPORT      │
├──────────────────────────────────────────┤
│ Auditor:   Codex AI Auditor              │
│ Score:     94.5 / 100                    │
│ Verdict:   [APPROVED]                    │
│                                          │
│ Findings:                                │
│  • [SEC-LOW] Add rate limiting headers   │
│  • [QUAL-INFO] Type hints in service.py  │
│                                          │
│ [1] Accept Report  [2] Trigger Repair    │
╰──────────────────────────────────────────╯
```

---

## 6. Verification & Test Strategy
- Unit tests for `ReviewFinding` and `ReviewReport` Pydantic models.
- Unit tests for `BaseReviewerAdapter`, `MockReviewerAdapter`, and `OllamaReviewerAdapter`.
- Unit tests for `ReviewEngine` managing automated review-repair cycles.
- Tests for `ReviewDashboard` UI rendering and report formatting.
