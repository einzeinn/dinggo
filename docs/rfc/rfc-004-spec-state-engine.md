# RFC-004: Specification Model & Persistent State Engine

## Status
**Proposed & Accepted**

## 1. Summary
RFC-004 defines the foundational data models and state management architecture for Dinggo's transformation into an **AI Product Factory**. This includes:
1. Standardized specification directory structure (`spec/`) and requirement ID traceability.
2. Specification parser and Pydantic data models for product requirements, architecture, API, UI, data models, and acceptance criteria.
3. Persistent State Machine (`.dinggo/state.yaml`) to enable *state-aware*, *resumable* pipeline sessions.
4. Project stack and AI provider discovery engine (`core/detector.py`).

---

## 2. Specification Directory Structure & Schema

The primary source of truth for Dinggo is the structured specification directory located in the project root:

```text
project-root/
├── spec/
│   ├── product.md          # High-level vision, user targets, problem statement, scope
│   ├── requirements.md     # Traceable requirements list (YAML frontmatter + markdown)
│   ├── architecture.md     # Frameworks, service boundaries, database, constraints
│   ├── ui.md               # Visual specs, theme, screens, components, user flows
│   ├── api.md              # Endpoints, schemas, auth protocols
│   ├── data-model.md       # Entities, fields, relationships, migrations
│   └── acceptance.md       # Verification criteria for requirement completion
└── dinggo.yaml             # Product Factory project configuration
```

### Requirement Identification Standard
Every discrete functional and non-functional requirement must have a globally unique identifier formatted as `<DOMAIN>-<NUMBER>`:
- `AUTH-001`: User authentication before accessing dashboard.
- `INV-001`: Create inventory items with SKU and quantity.
- `API-002`: Rate-limiting on public query endpoints.
- `SEC-001`: Role-based access control (RBAC).

This identifier is tracked through every layer:
$$\text{Requirement (ID)} \longrightarrow \text{Task (DAG)} \longrightarrow \text{Code (Files)} \longrightarrow \text{Tests} \longrightarrow \text{Validation} \longrightarrow \text{Review}$$

---

## 3. Pydantic Models (`core/spec/models.py`)

```python
class RequirementItem(BaseModel):
    id: str
    title: str
    description: str
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    category: str = "functional"
    acceptance_criteria: List[str] = Field(default_factory=list)

class ProductSpec(BaseModel):
    name: str
    version: str = "0.1.0"
    summary: str
    target_users: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    requirements: List[RequirementItem] = Field(default_factory=list)
    architecture: Dict[str, Any] = Field(default_factory=dict)
    raw_files: Dict[str, str] = Field(default_factory=dict)
```

---

## 4. Persistent State Machine (`.dinggo/state.yaml`)

Dinggo is state-aware. State transitions are stored persistently in `.dinggo/state.yaml`:

### Pipeline Phases
- `IDLE`: No active job.
- `SPEC_DISCOVERY`: Analyzing specification files.
- `PLANNING`: Generating task dependency graph.
- `APPROVAL_GATE_1`: Waiting for user approval on execution plan.
- `IMPLEMENTING`: Executing tasks across workers.
- `TESTING`: Running automated unit/integration/lint tests.
- `REPAIRING`: Active self-repair loop on test failures.
- `VALIDATING`: Checking requirement completeness & traceability.
- `APPROVAL_GATE_2`: Waiting for user approval on build validation.
- `BUILDING`: Compiling production artifacts and Docker images.
- `APPROVAL_GATE_3`: Waiting for user approval before export.
- `EXPORTING`: Generating distribution package in `dist/`.
- `REVIEWING`: Codex / independent reviewer analysis.
- `REVIEW_REPAIRING`: Self-repair loop on reviewer findings.
- `COMPLETED`: Pipeline finished, product ready.
- `FAILED`: Unrecoverable error / human intervention required.

### State Schema
```yaml
project:
  name: "inventory-app"
  root_path: "/path/to/project"
  phase: "PLANNING"
  status: "IN_PROGRESS"
  updated_at: "2026-08-17T16:00:00Z"
session:
  id: "DNG-SESS-20260817-001"
  can_resume: true
  active_task_id: "TASK-012"
  active_step: 3
  repair_cycle: 1
  max_repair_cycles: 3
stats:
  requirements_total: 27
  requirements_passed: 0
  tasks_total: 45
  tasks_completed: 12
  tests_total: 80
  tests_passed: 80
```

---

## 5. Project & AI Provider Detector (`core/detector.py`)

Pendeteksi lingkungan memeriksa:
1. **Project Stack**:
   - Git repository detection (`.git`).
   - Project manifest discovery (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`, `requirements.txt`).
   - Framework classification (Next.js, React, FastAPI, Django, Flask, Express, Spring Boot, etc.).
2. **AI Provider Availability**:
   - `Codex CLI`: Check `which codex` / `codex --version`.
   - `Claude CLI`: Check `which claude` / `claude --version`.
   - `Ollama`: Check `http://localhost:11434/api/tags` and list local models (`qwen3.5`, `llama3`, etc.).
   - `Gemini CLI`: Check CLI presence.

---

## 6. Verification & Test Strategy
- Unit tests validating spec parser on valid and missing spec directories.
- Unit tests verifying YAML frontmatter parsing and requirement ID regex extraction.
- Unit tests for State Machine phase transitions, persistence to disk, and resumption.
- Mock tests for Project & Provider detector.
