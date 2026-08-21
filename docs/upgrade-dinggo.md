# Dinggo Product Factory

## 1. Vision

**Dinggo** is an AI Product Factory that transforms product specifications into production-ready software.

Dinggo is not just an AI coding assistant and not a conversational chat-to-code bot.

Dinggo uses a **specification-driven development** approach, where users define products through specification documents that act as the source of truth throughout the entire build lifecycle.

### Core Principle

> **Define the product once. Let Dinggo build it.**

The primary input to Dinggo is not chat prompts, but a collection of structured specification documents such as:

* Product Requirements Document
* Functional Requirements
* Architecture Specification
* UI Specification
* API Specification
* Data Model
* Acceptance Criteria
* Technical Constraints

---

# 2. Product Positioning

### Traditional AI Coding Agent

```text
Prompt
  ↓
AI
  ↓
Code
```

### AI App Builder

```text
Prompt / Chat
  ↓
AI
  ↓
Application
```

### Dinggo

```text
Product Specification
        ↓
      PLAN
        ↓
   [APPROVAL]
        ↓
    IMPLEMENT
        ↓
      TEST
        ↓
   [VALIDATION]
        ↓
      BUILD
        ↓
 [FINAL APPROVAL]
        ↓
     EXPORT
        ↓
  INDEPENDENT REVIEW
```

Dinggo focuses on a **production pipeline**, rather than mere raw code generation.

---

# 3. Core Architecture

```text
                         HUMAN
                           │
                           ▼
                 PRODUCT SPECIFICATION
                           │
                           ▼
                      CONTEXTIX
                           │
                  Project Understanding
                           │
                           ▼
                    DINGGO PLANNER
                           │
                           ▼
                    EXECUTION PLAN
                           │
                     [APPROVAL]
                           │
                           ▼
                 ┌───────────────────┐
                 │  IMPLEMENTATION   │
                 │                   │
                 │ Backend           │
                 │ Frontend          │
                 │ Database          │
                 │ Infrastructure    │
                 │ Documentation     │
                 └─────────┬─────────┘
                           │
                           ▼
                         TEST
                           │
                           ▼
                      VALIDATOR
                           │
                    ┌──────┴──────┐
                    │             │
                  PASS          FAIL
                    │             │
                    │             ▼
                    │       REPAIR ENGINE
                    │             │
                    │             ▼
                    │            TEST
                    │
                    ▼
                        BUILD
                           │
                           ▼
                   [FINAL APPROVAL]
                           │
                           ▼
                        EXPORT
                           │
                           ▼
                   CODEX REVIEWER
                           │
                    ┌──────┴──────┐
                    │             │
                   PASS        FINDINGS
                    │             │
                    ▼             ▼
                 RELEASE      REPAIR LOOP
```

---

# 4. Pipeline

## Phase 1: SPEC

Dinggo menerima specification sebagai source of truth.

Contoh struktur:

```text
project/
├── spec/
│   ├── product.md
│   ├── requirements.md
│   ├── architecture.md
│   ├── ui.md
│   ├── api.md
│   ├── data-model.md
│   └── acceptance.md
│
└── dinggo.yaml
```

### `product.md`

Menjelaskan:

* tujuan produk
* target user
* masalah yang diselesaikan
* fitur utama
* scope produk

### `requirements.md`

Menjelaskan requirement yang dapat diverifikasi.

Example:

```yaml
requirements:
  - id: AUTH-001
    description: User must authenticate before accessing dashboard
    priority: critical

  - id: INV-001
    description: Admin can create inventory items
    priority: high
```

### `architecture.md`

Menentukan:

* framework
* runtime
* database
* service boundaries
* architecture constraints
* integration requirements

### `acceptance.md`

Menentukan kondisi yang harus terpenuhi agar requirement dianggap selesai.

---

# 5. SPEC as Contract

Setiap requirement mendapatkan identifier unik.

```text
AUTH-001
AUTH-002
INV-001
INV-002
```

Requirement ID tersebut harus dapat dilacak sepanjang pipeline:

```text
Requirement
    ↓
Plan
    ↓
Implementation
    ↓
Test
    ↓
Validation
    ↓
Review
```

Example:

```text
INV-001
   │
   ├── Task: TASK-023
   ├── Files: inventory/service.py
   ├── Tests: TEST-041
   ├── Validation: PASS
   └── Code Review: PASS
```

Tujuannya adalah menciptakan **traceability** antara requirement dan implementation.

---

# 6. Phase 2: PLAN

Planner membaca seluruh specification dan menghasilkan execution plan.

Output:

```text
PLAN
├── Architecture
├── Components
├── Dependencies
├── Tasks
├── Task Dependencies
├── Test Strategy
└── Validation Strategy
```

Example:

```text
TASK-001
  Setup project

TASK-002
  Implement database

TASK-003
  Implement authentication
      └── depends_on TASK-002

TASK-004
  Implement dashboard
      └── depends_on TASK-003

TASK-005
  Implement inventory
      └── depends_on TASK-002
```

Planner menghasilkan **task graph**, bukan sekadar daftar TODO.

---

# 7. Approval Gate 1

Before implementation begins, Dinggo displays the execution plan.

Example:

```text
╭──────────────────────────────────────╮
│         DINGGO PLAN REVIEW           │
├──────────────────────────────────────┤
│ Project: Inventory Management        │
│                                      │
│ Requirements: 27                     │
│ Tasks: 83                             │
│ Dependencies: 14                     │
│ Architecture: Next.js + FastAPI      │
│ Database: PostgreSQL                  │
│                                      │
│ [ APPROVE PLAN ]                     │
╰──────────────────────────────────────╯
```

Users can:

* approve
* reject
* modify specification
* regenerate plan

Dinggo **must not begin implementation before explicit approval** in default mode.

---

# 8. Phase 3: IMPLEMENT

Once the plan is approved, Dinggo executes the task graph.

Implementation can utilize specialized AI workers.

```text
                    DINGGO
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
      Backend       Frontend      Database
       Agent          Agent          Agent
         │             │             │
         └─────────────┼─────────────┘
                       ▼
                  Integration
```

Workers can be swapped based on model requirements.

Dinggo acts as the **orchestrator**, rather than being tied to a single monolithic model.

---

# 9. Phase 4: TEST

After implementation completes, Dinggo executes automated testing.

Testing can encompass:

* unit test
* integration test
* API test
* UI test
* type checking
* linting
* build validation
* dependency validation

Example:

```text
TEST RESULT

Unit Tests        124 PASS
Integration Tests  31 PASS
API Tests          18 PASS
Type Check          PASS
Lint                PASS
Build               PASS

Total: 174/174
```

---

# 10. Self-Repair Loop

If tests fail, Dinggo does not immediately abort.

```text
TEST
 ↓
FAILURE
 ↓
ERROR ANALYZER
 ↓
ROOT CAUSE
 ↓
REPAIR PLAN
 ↓
PATCH
 ↓
TEST
```

The repair loop enforces a maximum attempt threshold to prevent infinite execution.

Example:

```yaml
repair:
  enabled: true
  max_attempts: 5
```

If failures persist after the retry threshold:

```text
REPAIR FAILED

Attempts: 5/5

Remaining failures:
- TEST-041
- TEST-067

Pipeline paused.
Human intervention required.
```

---

# 11. Phase 5: VALIDATION

Testing verifies that the software functions technically.

Validation verifies that the software satisfies the product specification.

```text
SPECIFICATION
      │
      ▼
REQUIREMENT VALIDATOR
      │
      ▼
Traceability Check
      │
      ├── Requirement coverage
      ├── Acceptance criteria
      ├── Architecture constraints
      └── Feature completeness
```

Example:

```text
VALIDATION

Requirements:
  27/27 satisfied

Acceptance Criteria:
  41/41 satisfied

Architecture Constraints:
  12/12 satisfied

Status:
  PASS
```

---

# 12. Approval Gate 2

Prior to final build:

```text
╭──────────────────────────────────────╮
│       DINGGO VALIDATION REVIEW       │
├──────────────────────────────────────┤
│ Requirements       27/27 PASS        │
│ Acceptance         41/41 PASS        │
│ Tests             174/174 PASS       │
│ Architecture       12/12 PASS        │
│                                      │
│ [ APPROVE BUILD ]                    │
╰──────────────────────────────────────╯
```

---

# 13. Phase 6: BUILD

Dinggo generates production artifacts.

Example:

```text
BUILD
├── Application
├── Docker Image
├── Production Bundle
├── Database Migration
├── Documentation
└── Deployment Configuration
```

Builds must be reproducible from specifications and persistent project state.

---

# 14. Approval Gate 3

Final approval before export or deployment.

```text
FINAL REVIEW

Build:             PASS
Tests:             174/174
Requirements:      27/27
Validation:        PASS
Security Checks:   PASS

Ready for export.

[ EXPORT ]
```

---

# 15. Phase 7: EXPORT

Dinggo can generate:

```text
Web Application
Mobile Application
CLI Tool
API
Library
Package
AI Agent
Automation
Internal Tool
Microservice
```

Exports can include:

```text
dist/
├── source/
├── build/
├── artifacts/
├── documentation/
└── manifest.json
```

---

# 16. Codex as Independent Reviewer

Dinggo is not the sole entity judging the quality of output.

After export/build completes, Dinggo invokes an **independent reviewer engine** for code audit.

```text
             DINGGO
                │
                ▼
             PRODUCT
                │
                ▼
          CODEX REVIEWER
                │
      ┌─────────┼─────────┐
      ▼         ▼         ▼
 Requirements  Code     Security
    Review     Review     Review
      │         │         │
      └─────────┼─────────┘
                ▼
           REVIEW REPORT
```

The reviewer is isolated as an independent auditor, separate from implementation workers.

The goal is to eliminate self-evaluation bias.

---

# 17. Review Categories

The reviewer inspects:

### Requirement Review

* requirement completeness
* acceptance criteria
* missing functionality
* unexpected behavior

### Code Review

* correctness
* maintainability
* duplication
* code smell
* architecture violations

### Security Review

* secrets
* authentication
* authorization
* injection
* unsafe API usage
* dependency vulnerabilities

### Architecture Review

* architecture consistency
* unnecessary complexity
* dependency boundaries
* scalability concerns

---

# 18. Machine-Readable Review Result

The review outputs a structured, machine-readable format:

Example:

```yaml
review:
  status: failed

requirements:
  passed: 25
  failed: 2

security:
  critical: 0
  high: 1
  medium: 3

architecture:
  score: 8.4

code_quality:
  score: 8.8

findings:
  - id: SEC-001
    severity: high
    file: auth/service.py
    issue: Unauthorized access possible

  - id: REQ-014
    severity: medium
    issue: Acceptance criterion not fully implemented
```

---

# 19. Review Repair Loop

If findings or issues are detected:

```text
CODEX
  ↓
REVIEW REPORT
  ↓
DINGGO REPAIR ENGINE
  ↓
PATCH
  ↓
TEST
  ↓
VALIDATION
  ↓
CODEX REVIEW
```

The pipeline is marked complete only when the reviewer returns:

```text
PASS
```

or remaining findings are within accepted severity thresholds.

---

# 20. Multi-Agent Architecture

Dinggo is model-agnostic.

```text
                    DINGGO ORCHESTRATOR
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
      Planner Agent    Implementation     Validation
                            Agent             Agent
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                            ▼
                     External Reviewer
                         / Codex
```

Each agent possesses clear, decoupled responsibilities.

### Planner

Transforms specifications into an execution plan.

### Implementation Agent

Generates and modifies source code.

### Test Agent

Authors and executes tests.

### Validation Agent

Verifies requirement traceability.

### Repair Agent

Repairs failures via automated patching.

### Reviewer

Conducts independent quality and security assessment.

---

# 21. Contextix Integration

Contextix acts as the **project intelligence layer** for Dinggo.

```text
                 SPECIFICATION
                       │
                       ▼
                    CONTEXTIX
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
          Context   Relations   Metadata
             │         │         │
             └─────────┼─────────┘
                       ▼
                  DINGGO PLAN
```

Contextix is responsible for:

* parsing project documentation
* context generation
* project relationships
* dependency understanding
* repository indexing
* structured project knowledge

Dinggo is responsible for:

* planning
* execution
* testing
* validation
* building
* export

Thus:

> **Contextix understands. Dinggo executes.**

---

# 22. Source of Truth

Dinggo enforces a source of truth hierarchy:

```text
1. Specification
2. Approved Plan
3. Source Code
4. Tests
5. Generated Artifacts
```

If source code conflicts with specifications, specifications take precedence.

If implementation requires altering specifications, Dinggo must request human approval or update specifications via an explicit change process.

---

# 23. Execution Modes

### Safe Mode

```bash
dinggo execute
```

Requires approval at each gate.

### Autonomous Mode

```bash
dinggo execute --autonomous
```

Dinggo can bypass specific gates based on configured policy.

### Governed Mode

```bash
dinggo execute --policy enterprise.yaml
```

Example:

```yaml
approval:
  architecture: required
  database_migration: required
  production_deploy: required

security:
  critical_failure: block
  high_failure: block

review:
  required: true
```

---

# 24. CLI Concept

```bash
dinggo init
dinggo spec validate
dinggo plan
dinggo plan --approve
dinggo execute
dinggo test
dinggo validate
dinggo build
dinggo review
dinggo export
```

Or one-shot pipeline:

```bash
dinggo execute
```

With pipeline:

```text
SPEC
 ↓
PLAN
 ↓
APPROVAL
 ↓
IMPLEMENT
 ↓
TEST
 ↓
VALIDATE
 ↓
BUILD
 ↓
FINAL APPROVAL
 ↓
EXPORT
 ↓
CODEX REVIEW
```

---

# 25. Long-Term Vision

Dinggo evolves from:

```text
AI Coding CLI
```

into:

```text
AI Product Engineering Engine
```

and ultimately:

```text
AI PRODUCT FACTORY
```

The ultimate goal is enabling developers to define a product clearly via specifications, with Dinggo handling the engineering process autonomously while retaining:

* human approval
* deterministic validation
* automated testing
* traceability
* independent review
* reproducible builds
* policy enforcement

### Final Concept

```text
                    HUMAN
                      │
                      │
                "Define Product"
                      │
                      ▼
              ┌───────────────┐
              │ SPECIFICATION │
              └───────┬───────┘
                      │
                      ▼
                  CONTEXTIX
                      │
                      ▼
                    PLAN
                      │
                 [APPROVAL]
                      │
                      ▼
                 IMPLEMENT
                      │
                      ▼
                    TEST
                      │
                      ▼
                 VALIDATION
                      │
                 [APPROVAL]
                      │
                      ▼
                    BUILD
                      │
                 [APPROVAL]
                      │
                      ▼
                   EXPORT
                      │
                      ▼
                CODEX REVIEW
                      │
              ┌───────┴───────┐
              ▼               ▼
             PASS          FINDINGS
              │               │
              ▼               ▼
          PRODUCT         DINGGO REPAIR
          RELEASE              │
                               └──────→ REVIEW
```

## Core Philosophy

> **Dinggo does not turn prompts into code.**
>
> **Dinggo turns specifications into products.**
