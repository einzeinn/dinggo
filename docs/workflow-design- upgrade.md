# Dinggo Product Factory - CLI Workflow Specification

## 1. Workflow Overview

Dinggo uses an **interactive CLI interface** as its primary interface for developers.

Core Workflow:

```text
Terminal
   ↓
cd <project>
   ↓
dinggo interface
   ↓
Dinggo Interface
   │
   ├── Wizard
   ├── Execute
   ├── Settings
   ├── Output
   ├── Review
   └── Exit
```

Dinggo also provides direct command-level interfaces for automation and CI/CD pipelines.

```text
Interactive CLI
      │
      ▼
Dinggo Engine
      ▲
      │
Direct CLI Commands
```

---

# 2. Entry Point

Developer enters the project directory:

```bash
cd my-project
```

Then executes:

```bash
dinggo interface
```

Dinggo performs initial environment detection.

```text
DINGGO PRODUCT FACTORY

Project:
my-project

Detecting...

✓ Git repository
✓ Project specification
✓ Contextix
✓ AI providers
✓ Build system
✓ Test system

Loading project...
```

Once initialization completes, Dinggo opens the main interface.

---

# 3. Main Interface

```text
╭────────────────────────────────────────╮
│             DINGGO                     │
│        AI PRODUCT FACTORY              │
├────────────────────────────────────────┤
│                                        │
│  > Wizard                              │
│    Execute                             │
│    Settings                            │
│    Output                              │
│    Review                              │
│    Exit                                │
│                                        │
╰────────────────────────────────────────╯
```

The menu serves as the primary entrypoint for the entire workflow.

---

# 4. Wizard Workflow

Wizard digunakan untuk:

* project initialization
* specification discovery
* provider detection
* configuration
* plan generation
* plan approval

Flow:

```text
Wizard
  ↓
Project Detection
  ↓
Specification Detection
  ↓
Provider Detection
  ↓
Configuration Validation
  ↓
Context Generation
  ↓
Plan Generation
  ↓
Plan Review
  ↓
[APPROVAL]
```

---

## 4.1 Project Detection

Dinggo mendeteksi project yang sedang aktif.

Contoh:

```text
PROJECT DETECTION

Path:
~/projects/inventory-app

✓ Git
✓ package.json
✓ backend
✓ frontend
✓ database configuration

Project type:
Full-stack application
```

Jika project belum memiliki specification:

```text
No specification found.

Dinggo can initialize:

spec/
├── product.md
├── requirements.md
├── architecture.md
├── ui.md
├── api.md
└── acceptance.md

[Initialize Specification]
```

---

# 5. Provider Detection

Dinggo otomatis mendeteksi AI provider yang tersedia.

```text
AI PROVIDER DISCOVERY

✓ Codex CLI
✓ Claude CLI
✓ Ollama
✗ Gemini CLI

Local models:
✓ qwen3.5
✓ llama3
✓ gemma-sea-lion
```

Provider detection dapat menggunakan:

```text
CLI Detection
Environment Detection
Local Server Detection
Configuration Detection
```

Hasil detection disimpan dalam Provider Registry.

---

# 6. Provider Setup

Setelah provider ditemukan, Dinggo melakukan configuration wizard.

```text
PROVIDER SETUP

Provider: Codex

Authentication:
✓ Authenticated

Capabilities:
✓ Code Review
✓ Repository Analysis

Set as default reviewer?

> Yes
  No
```

Untuk local provider:

```text
PROVIDER SETUP

Provider: Ollama

Endpoint:
http://localhost:11434

Available Models:

> qwen3.5
  llama3
  gemma-sea-lion
```

Konfigurasi disimpan secara otomatis.

Users do not need to manually configure environment variables.

---

# 7. Context Generation

Setelah configuration selesai:

```text
Generating project context...

Parser
  ↓
Analyzer
  ↓
Linker
  ↓
Validator
  ↓
Context Builder

✓ Repository analyzed
✓ Documentation analyzed
✓ Dependencies analyzed
✓ Project context generated
```

Contextix menjadi project intelligence layer.

```text
Specification
      ↓
Contextix
      ↓
Structured Project Context
      ↓
Dinggo Planner
```

---

# 8. Plan Generation

Dinggo membaca specification dan context untuk membuat execution plan.

```text
Generating execution plan...

Requirements:
27

Components:
14

Tasks:
83

Dependencies:
19
```

Plan menghasilkan task graph.

```text
TASK-001
  Setup project

TASK-002
  Setup database
      ↓
TASK-003
  Authentication
      ↓
TASK-004
  Dashboard

TASK-005
  Inventory
```

---

# 9. Plan Review

Dinggo menampilkan plan sebelum implementation.

```text
PLAN REVIEW

Project:
Inventory App

Requirements:
27

Tasks:
83

Architecture:
Next.js
FastAPI
PostgreSQL

Estimated execution:
~83 tasks

[View Plan]
[Approve]
[Revise]
[Cancel]
```

### Approval

Jika user memilih `Approve`:

```text
Plan approved.

Execution can begin.
```

Jika memilih `Revise`:

```text
PLAN REVISION

What should be changed?

> Add notification service
```

Dinggo memperbarui plan tanpa mengubah specification secara otomatis.

---

# 10. Execute Workflow

Execute menjalankan execution plan.

```text
Execute
   ↓
Task Scheduler
   ↓
Implementation Workers
   ↓
Testing
   ↓
Repair
   ↓
Validation
   ↓
Build
```

---

## 10.1 Execution Interface

```text
DINGGO EXECUTION

Project:
Inventory App

Phase:
IMPLEMENTATION

Progress:
██████████████░░░░ 72%

Tasks:
60/83

Current:
TASK-047

Implement inventory dashboard

Worker:
Implementation Agent
```

User dapat melihat:

```text
[Pause]
[View Logs]
[View Task]
[Cancel]
```

---

# 11. Implementation Workflow

Dinggo menjalankan task berdasarkan dependency graph.

```text
Task Graph
    ↓
Task Scheduler
    ↓
Worker Selection
    ↓
Implementation
    ↓
File Changes
    ↓
Task Validation
```

Setiap task menghasilkan execution record.

```yaml
task:
  id: TASK-047
  requirement: INV-003
  status: completed

files:
  - src/inventory/dashboard.tsx

tests:
  - TEST-091

validation:
  status: pass
```

---

# 12. Test Workflow

Setelah implementation:

```text
IMPLEMENTATION
      ↓
TEST RUNNER
      ↓
Unit Tests
      ↓
Integration Tests
      ↓
Type Check
      ↓
Lint
      ↓
Build Check
```

Contoh output:

```text
TEST RESULTS

Unit:
124 PASS

Integration:
31 PASS

API:
18 PASS

Type Check:
PASS

Lint:
PASS

Total:
174/174 PASS
```

---

# 13. Automatic Repair Workflow

If tests fail:

```text
TEST FAILURE
     ↓
Failure Analyzer
     ↓
Root Cause Detection
     ↓
Repair Plan
     ↓
Implementation Worker
     ↓
TEST AGAIN
```

Contoh:

```text
TEST FAILURE

TEST-091
Expected:
200

Received:
500

Analyzing...

Root cause:
Missing database initialization.

Repairing...

✓ Patch applied
✓ Test passed
```

Repair memiliki maximum cycle.

```text
Repair Cycle:
1/3
```

If all retry cycles fail:

```text
REPAIR FAILED

Attempts:
3/3

Pipeline paused.

[View Failure]
[Manual Fix]
[Abort]
```

---

# 14. Validation Workflow

Setelah seluruh test berhasil:

```text
TEST
 ↓
VALIDATION
```

Validator memeriksa:

```text
Requirements
Acceptance Criteria
Architecture
Dependencies
Configuration
Generated Artifacts
```

Output:

```text
VALIDATION

Requirements:
27/27 PASS

Acceptance:
41/41 PASS

Architecture:
12/12 PASS

Status:
PASS
```

---

# 15. Validation Approval

Sebelum build final:

```text
VALIDATION APPROVAL

✓ Requirements satisfied
✓ Tests passed
✓ Acceptance criteria passed
✓ Architecture valid

Ready to build?

[Approve Build]
[Revise]
[Cancel]
```

Jika disetujui:

```text
VALIDATION APPROVED
```

Dinggo melanjutkan ke build.

---

# 16. Build Workflow

```text
VALIDATED PROJECT
       ↓
BUILD ENGINE
       ↓
Compile
       ↓
Package
       ↓
Generate Artifacts
       ↓
Build Verification
```

Output:

```text
BUILD

✓ Frontend compiled
✓ Backend compiled
✓ Assets generated
✓ Docker image built
✓ Documentation generated

Build:
SUCCESS
```

---

# 17. Final Approval

Setelah build:

```text
FINAL APPROVAL

Project:
Inventory App

Tests:
174/174 PASS

Validation:
PASS

Build:
PASS

Requirements:
27/27 PASS

Ready for export.

[Approve Export]
[Review]
[Cancel]
```

User harus melakukan final approval dalam default mode.

---

# 18. Export Workflow

```text
FINAL APPROVAL
      ↓
EXPORT
      ↓
Generate Distribution
      ↓
Generate Manifest
      ↓
Generate Documentation
      ↓
Export Complete
```

Contoh:

```text
EXPORT COMPLETE

Build ID:
DNG-2026-0816-0042

Artifacts:

✓ source/
✓ build/
✓ docker/
✓ documentation/
✓ manifest.json

Output:
dist/
```

---

# 19. Review Workflow

Review dapat dijalankan setelah build atau export.

```text
Review
  ↓
Select Reviewer
  ↓
Review Engine
  ↓
Provider Adapter
  ↓
AI Reviewer
  ↓
Review Report
```

Provider dapat berupa:

```text
Codex
Claude
Gemini
Ollama
Local LLM
Custom Provider
```

---

# 20. Reviewer Selection

```text
REVIEW PROVIDER

Detected:

> Codex
  Claude
  Ollama
  Custom

Default:
Codex
```

The reviewer provider is decoupled from Dinggo core dependencies.

Review Engine menggunakan adapter.

```text
Review Engine
      ↓
Provider Adapter
      ↓
Selected Provider
```

---

# 21. Review Execution

```text
REVIEW

Provider:
Codex

Analyzing:

✓ Requirements
✓ Architecture
⟳ Security
○ Code Quality
○ Dependencies

Progress:
████████████░░░░ 68%
```

---

# 22. Review Result

```text
REVIEW RESULT

Status:
NEEDS REVISION

Requirements:
27/27 PASS

Architecture:
PASS

Security:
1 HIGH
2 MEDIUM

Code Quality:
3 FINDINGS
```

Findings:

```text
SEC-001
Severity: HIGH

File:
auth/service.py:42

Issue:
Missing authorization check.
```

---

# 23. Review Actions

After review:

```text
REVIEW ACTIONS

> Revise Automatically
  Review Again
  Ignore Findings
  Export Report
  Return
```

### Revise Automatically

```text
Review Findings
      ↓
Repair Plan
      ↓
Implementation
      ↓
Test
      ↓
Validation
      ↓
Review Again
```

---

# 24. Review-Repair Loop

```text
                 ┌───────────────┐
                 │ CODE REVIEW   │
                 └───────┬───────┘
                         │
                  ┌──────┴──────┐
                  │             │
                 PASS        FINDINGS
                  │             │
                  │             ▼
                  │       REPAIR ENGINE
                  │             │
                  │             ▼
                  │           TEST
                  │             │
                  │             ▼
                  │        VALIDATION
                  │             │
                  │             ▼
                  │        CODE REVIEW
                  │             │
                  └─────────────┘
```

Maximum review-repair cycles:

```yaml
review:
  max_repair_cycles: 3
```

Jika berhasil:

```text
FINAL REVIEW

✓ Codex PASS
✓ Requirements PASS
✓ Security PASS
✓ Tests PASS

Product ready.
```

---

# 25. Output Workflow

Menu `Output` menampilkan seluruh hasil pipeline.

```text
OUTPUT

> Latest Build
  Build History
  Logs
  Artifacts
  Review Reports
  Documentation
```

### Build History

```text
DNG-0042
✓ PASS
2026-08-16

DNG-0041
✗ BUILD FAILED
2026-08-15

DNG-0040
✓ PASS
2026-08-14
```

---

# 26. Settings Workflow

Settings menjadi pusat konfigurasi Dinggo.

```text
SETTINGS

> AI Providers
  Models
  Execution
  Approval
  Review
  Contextix
  Project
  Reset
```

### AI Providers

```text
PROVIDERS

✓ Codex
✓ Claude
✓ Ollama
✗ Gemini

[Detect Again]
[Configure]
[Remove]
```

### Execution Settings

```text
EXECUTION

Auto Repair:
ON

Max Repair Attempts:
3

Parallel Tasks:
4

Approval Mode:
Safe
```

### Review Settings

```text
REVIEW

Default Provider:
Codex

Review Required:
YES

Auto Revision:
YES

Max Review Cycles:
3
```

---

# 27. Project State

Dinggo menyimpan state pipeline.

```text
Project
  ↓
State Manager
  ↓
Current Phase
Current Plan
Current Task
Build History
Review History
```

Contoh:

```yaml
project:
  phase: review
  plan: approved
  execution: completed
  tests: passed
  validation: passed
  build: passed
  review: needs_revision
```

Jika Dinggo ditutup di tengah execution, pipeline dapat dilanjutkan.

```bash
dinggo interface
```

akan menampilkan:

```text
RESUMABLE SESSION FOUND

Project:
Inventory App

Last state:
REVIEW_REPAIR

Cycle:
2/3

> Resume
  Restart
  View State
```

---

# 28. Direct CLI Mode

Interactive interface bukan satu-satunya cara menggunakan Dinggo.

Command langsung tersedia untuk automation.

```bash
dinggo wizard
dinggo plan
dinggo execute
dinggo test
dinggo validate
dinggo build
dinggo review
dinggo export
```

Contoh CI/CD:

```bash
dinggo validate --non-interactive
dinggo build --non-interactive
dinggo review --non-interactive
```

---

# 29. Complete User Journey

Workflow normal:

```text
Terminal
   ↓
cd project
   ↓
dinggo interface
   ↓
Wizard
   ↓
Detect Project
   ↓
Detect Providers
   ↓
Validate Specification
   ↓
Generate Context
   ↓
Generate Plan
   ↓
[APPROVAL]
   ↓
Execute
   ↓
Implement
   ↓
Test
   ↓
Repair if needed
   ↓
Validate
   ↓
[APPROVAL]
   ↓
Build
   ↓
[FINAL APPROVAL]
   ↓
Export
   ↓
Review
   ↓
Findings?
   │
   ├── NO → Product Ready
   │
   └── YES
         ↓
      Revision
         ↓
       Test
         ↓
     Validation
         ↓
       Review
```

---

# 30. Main CLI Navigation

Final interactive structure:

```text
╭──────────────────────────────────────────╮
│              DINGGO                      │
│         AI PRODUCT FACTORY               │
├──────────────────────────────────────────┤
│                                          │
│  > Wizard                                │
│    Execute                               │
│    Settings                              │
│    Output                                │
│    Review                                │
│    Exit                                  │
│                                          │
├──────────────────────────────────────────┤
│ Project: inventory-app                   │
│ Phase: REVIEW                            │
│ Status: NEEDS REVISION                   │
╰──────────────────────────────────────────╯
```

Dinggo interface harus selalu memperlihatkan:

* current project
* current phase
* current execution state
* latest build status
* latest review status
* resumable session jika tersedia

---

# 31. Design Principles

### 1. Specification First

Specification menjadi source of truth.

### 2. Approval Driven

Critical transitions membutuhkan human approval secara default.

### 3. State Aware

Dinggo harus dapat mengetahui posisi terakhir pipeline dan melanjutkannya.

### 4. Provider Agnostic

AI provider dapat diganti tanpa mengubah workflow Dinggo.

### 5. Review Independent

Reviewer merupakan komponen terpisah dari implementation engine.

### 6. Machine + Human Friendly

Interactive CLI untuk manusia, direct CLI untuk automation.

### 7. Recoverable

Failures do not require restarting the entire pipeline from scratch.

### 8. Traceable

Requirement → Task → Code → Test → Validation → Review harus dapat ditelusuri.

---

# 32. Final Workflow

```text
                         DINGGO
                            │
                            ▼
                     ┌────────────┐
                     │  WIZARD    │
                     └─────┬──────┘
                           │
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
          PROJECT         SPEC         PROVIDER
          DETECT         DETECT         DETECT
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                       CONTEXTIX
                           │
                           ▼
                          PLAN
                           │
                       [APPROVAL]
                           │
                           ▼
                        EXECUTE
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                IMPLEMENT       TEST
                    │             │
                    └──────┬──────┘
                           ▼
                        REPAIR
                           │
                           ▼
                       VALIDATE
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
                        REVIEW
                           │
                    ┌──────┴──────┐
                    ▼             ▼
                  PASS        FINDINGS
                    │             │
                    ▼             ▼
              PRODUCT READY    REVISE
                                  │
                                  ▼
                                TEST
                                  │
                                  ▼
                              VALIDATE
                                  │
                                  ▼
                               REVIEW
```

**Core interaction:**

```text
Human defines.
Dinggo plans.
Human approves.
Dinggo builds.
Tests validate.
Dinggo repairs.
Human approves.
Dinggo exports.
Independent reviewer checks.
Dinggo revises if necessary.
Product ships.
```
