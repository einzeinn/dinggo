# Dinggo Product Factory

## 1. Vision

**Dinggo** adalah AI Product Factory yang mengubah spesifikasi produk menjadi software yang siap digunakan.

Dinggo bukan sekadar AI coding assistant dan bukan chatbot untuk membuat aplikasi melalui percakapan.

Dinggo menggunakan pendekatan **specification-driven development**, di mana pengguna mendefinisikan produk melalui file spesifikasi yang menjadi source of truth selama seluruh proses pembangunan.

### Core Principle

> **Define the product once. Let Dinggo build it.**

Input utama Dinggo bukan chat, melainkan kumpulan dokumen terstruktur seperti:

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

Dinggo berfokus pada **production pipeline**, bukan sekadar generation.

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

Contoh:

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

Contoh:

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

Contoh:

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

Sebelum implementation dimulai, Dinggo menampilkan execution plan.

Contoh:

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

User dapat:

* approve
* reject
* modify specification
* regenerate plan

Dinggo **tidak boleh melakukan implementation sebelum approval** dalam default mode.

---

# 8. Phase 3: IMPLEMENT

Setelah plan disetujui, Dinggo menjalankan task graph.

Implementation dapat menggunakan beberapa AI worker.

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

Worker dapat diganti berdasarkan kebutuhan model.

Dinggo bertindak sebagai **orchestrator**, bukan harus menjadi model tunggal.

---

# 9. Phase 4: TEST

Setelah implementation selesai, Dinggo menjalankan automated testing.

Testing dapat mencakup:

* unit test
* integration test
* API test
* UI test
* type checking
* linting
* build validation
* dependency validation

Contoh:

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

Jika test gagal, Dinggo tidak langsung berhenti.

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

Loop memiliki batas maksimum untuk mencegah infinite execution.

Contoh:

```yaml
repair:
  enabled: true
  max_attempts: 5
```

Jika gagal setelah batas:

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

Testing hanya memastikan software berfungsi secara teknis.

Validation memastikan software sesuai dengan specification.

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

Contoh:

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

Sebelum build final:

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

Dinggo menghasilkan production artifacts.

Contoh:

```text
BUILD
├── Application
├── Docker Image
├── Production Bundle
├── Database Migration
├── Documentation
└── Deployment Configuration
```

Build harus dapat direproduksi dari specification dan project state.

---

# 14. Approval Gate 3

Final approval sebelum export/deployment.

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

Dinggo dapat menghasilkan:

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

Export dapat berupa:

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

Dinggo tidak menjadi satu-satunya pihak yang menentukan kualitas hasil.

Setelah export/build selesai, Dinggo dapat memanggil **Codex sebagai independent reviewer**.

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

Codex harus diposisikan sebagai **reviewer**, bukan bagian dari implementation worker yang sama.

Tujuannya mengurangi bias dari self-evaluation.

---

# 17. Review Categories

Codex reviewer dapat memeriksa:

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

Review harus menghasilkan format yang dapat diproses Dinggo.

Contoh:

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

Jika Codex menemukan masalah:

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

Pipeline hanya dianggap selesai setelah reviewer memberikan:

```text
PASS
```

atau finding yang tersisa berada di bawah threshold yang telah ditentukan.

---

# 20. Multi-Agent Architecture

Dinggo harus bersifat model-agnostic.

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

Setiap agent memiliki responsibility yang jelas.

### Planner

Mengubah specification menjadi execution plan.

### Implementation Agent

Menulis dan memodifikasi source code.

### Test Agent

Membuat dan menjalankan test.

### Validation Agent

Memverifikasi requirement.

### Repair Agent

Memperbaiki failure.

### Reviewer

Melakukan independent quality assessment.

---

# 21. Contextix Integration

Contextix menjadi **project intelligence layer** untuk Dinggo.

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

Contextix bertanggung jawab terhadap:

* parsing project documentation
* context generation
* project relationships
* dependency understanding
* repository indexing
* structured project knowledge

Dinggo bertanggung jawab terhadap:

* planning
* execution
* testing
* validation
* building
* export

Dengan demikian:

> **Contextix understands. Dinggo executes.**

---

# 22. Source of Truth

Dinggo memiliki hierarchy source of truth:

```text
1. Specification
2. Approved Plan
3. Source Code
4. Tests
5. Generated Artifacts
```

Jika source code bertentangan dengan specification, specification menjadi acuan utama.

Jika implementation membutuhkan perubahan terhadap specification, Dinggo harus meminta approval atau memperbarui specification melalui explicit change process.

---

# 23. Execution Modes

### Safe Mode

```bash
dinggo execute
```

Memerlukan approval pada setiap gate.

### Autonomous Mode

```bash
dinggo execute --autonomous
```

Dinggo dapat melewati approval tertentu berdasarkan policy.

### Governed Mode

```bash
dinggo execute --policy enterprise.yaml
```

Contoh:

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

Atau one-shot pipeline:

```bash
dinggo execute
```

Dengan pipeline:

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

Dinggo berkembang dari:

```text
AI Coding CLI
```

menjadi:

```text
AI Product Engineering Engine
```

dan akhirnya:

```text
AI PRODUCT FACTORY
```

Tujuan akhirnya adalah memungkinkan seseorang mendefinisikan sebuah produk secara jelas melalui specification, lalu Dinggo menangani sebagian besar proses engineering secara autonomous dengan tetap memiliki:

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
