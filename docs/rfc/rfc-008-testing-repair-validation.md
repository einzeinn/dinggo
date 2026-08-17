# RFC-008: Automated Testing, Self-Repair Engine & Validation Gate 2

## Status
**Proposed & Accepted**

## 1. Summary
RFC-008 defines the architecture for Dinggo's **Multi-Tier Test Runner**, **Automated Closed-Loop Self-Repair Engine**, and **Specification Traceability Validator (Approval Gate 2)**.
It ensures that software is technically validated through automated testing, automatically repaired upon failure within configured attempt bounds, and verified against the specification source of truth before triggering the build phase.

---

## 2. Multi-Tier Test Runner (`core/testing/test_runner.py`)

The Test Runner executes across multiple test tiers:

```text
IMPLEMENTATION
      ↓
TEST RUNNER
      ├── Unit Tests (pytest / unittest / npm test)
      ├── Integration Tests
      ├── Type Check (mypy / tsc)
      ├── Linter (ruff / flake8 / eslint)
      └── Build Check
```

### Data Schema
```python
class TestFailure(BaseModel):
    test_id: str
    test_name: str
    error_message: str
    stack_trace: str
    target_file: Optional[str] = None
    line_number: Optional[int] = None

class TestRunSummary(BaseModel):
    total_tests: int
    passed_tests: int
    failed_tests: int
    tier_results: Dict[str, bool] = Field(default_factory=dict)
    failures: List[TestFailure] = Field(default_factory=list)
    success: bool
```

---

## 3. Closed-Loop Self-Repair Engine (`core/repair/`)

When a test failure occurs, Dinggo does not halt immediately; it enters the automated repair cycle:

```text
TEST
 ↓
FAILURE
 ↓
ERROR ANALYZER (root cause & stack trace diagnosis)
 ↓
REPAIR PLAN (patch strategy)
 ↓
PATCH APPLICATION (code modification)
 ↓
RETEST (Cycle N / max_attempts)
```

- **Cycle Control**: Configured via `dinggo.yaml` (`repair.max_attempts`, default 5).
- **Circuit Breaker**: If `attempts >= max_attempts`, the pipeline transitions to `PAUSED` and requests human intervention.

---

## 4. Specification Requirement Validator (`core/validation/requirement_validator.py`)

Validation ensures that technical implementation matches the original product specification:

```text
SPECIFICATION
      │
      ▼
REQUIREMENT VALIDATOR
      ├── Requirement Traceability (e.g. AUTH-001, INV-001)
      ├── Acceptance Criteria Checks (e.g. ACC-001)
      ├── Architecture Constraints Verification
      └── Feature Completeness Matrix
```

---

## 5. Approval Gate 2 (Validation Review) (`cli/gates/validation_review.py`)

Before proceeding to artifact compilation and production packaging (Phase 6):

```text
╭──────────────────────────────────────────╮
│       DINGGO VALIDATION REVIEW (GATE 2)  │
├──────────────────────────────────────────┤
│ Requirements       27/27 PASS            │
│ Acceptance         41/41 PASS            │
│ Tests             174/174 PASS           │
│ Architecture       12/12 PASS            │
│                                          │
│ [1] Approve Build                        │
│ [2] Revise & Retest                      │
│ [3] Cancel                               │
╰──────────────────────────────────────────╯
```

---

## 6. Verification & Test Strategy
- Unit tests for `TestRunner` parsing test outputs and failure diagnostics.
- Unit tests for `RepairEngine` executing simulated failure -> patch -> retest cycles within max attempts.
- Unit tests for `RequirementValidator` matching `ProductSpec` requirements and acceptance criteria.
- Tests for `ValidationReviewGate` interactive and headless approval transitions.
