# 02 - Product Requirements Document

## Summary

A local CLI IDE and Product Factory orchestrating 3 models (intent parsing, planning/task-graphing, codegen) that executes the core loop: **reason → plan → user confirm → execute**.

## User Flow (Core Loop)

```text
$ cd myproject/
$ dinggo                  # Launch CLI IDE
> [user enters casual or natural language prompt]
  → [Layer 1: Intent Parsing] parses user intent into structured JSON
  → [Layer 2: Planner] reasons & builds step-by-step DAG plan
  → displays plan to user
> [user confirms or provides revisions]
  → [Layer 3: Executor] executes sandboxed tool calls according to plan
  → displays results (diff, command output, etc.)
```

## Core Features (v1 — MVP)

### F1. Intent Parsing
- Accepts natural language instructions (including casual Indonesian & English)
- Converts input into structured requests (task type, target file/scope, constraints)

### F2. Reasoning & Planning
- Reasoning model with thinking mode to break down tasks into discrete steps
- Formats plans clearly (numbered steps, action type, target file per step)
- **Mandatory pause**: awaits user confirmation before executing state-modifying actions

### F3. Plan Confirmation & Revision
- User options: `[Y] Execute`, `[N] Cancel`, or `[R] Revise` with free-form text feedback (re-generates plan incorporating feedback)

### F4. Tool Calling & Execution
Minimum tools available in v1:
- `read_file(path)`
- `write_file(path, content)`
- `list_dir(path)`
- `run_command(cmd)` — sandboxed execution with confirmation for destructive commands
- `edit_file(path, diff)` — applies SEARCH/REPLACE blocks with atomic fallback

### F5. Codegen Delegation
- Plan steps requiring Python code generation are delegated to a dedicated codegen model (see `06-Architecture.md`)

### F6. Session & Context Awareness
- Aware of current project root (working directory)
- Contextix memory adapter (`.context/`) injects project constraints, decisions, and knowledge graphs

## Non-Core Features (Post-v1)

- Session history / replay
- Multi-language runtime support (beyond Python)
- Automated changelog generator based on RFC-001

## Out of Scope (v1)

- Remote / cloud model fallback
- Multi-user / auth
- GUI editor

## Technical Constraints

- Operates within 16GB RAM constraints (CPU / integrated GPU support)
- Models orchestrated via Ollama with sequential layer transitions (`keep_alive: 0`)
- Implementation language: Python

## Success Metrics

- Generated plans are clear, actionable, and adhere to project architecture
- Strict zero-tolerance for unconfirmed plan execution (safety requirement)
- Fast and responsive prompt-to-plan generation
