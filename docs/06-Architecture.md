# 06 - Architecture

## Overview

Dinggo employs a 3-layer model orchestration architecture, where each model specializes in a dedicated phase. Models are loaded sequentially rather than concurrently to fit within 16GB RAM hardware limits.

```text
┌─────────────────────────────────────────────────────────────┐
│  USER (terminal, casual natural language)                   │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1 — Intent Parsing                                   │
│  Model: Gemma-SEA-LION-V4.5-E2B-IT (Q4_K_M)                 │
│  Role: parse casual user prompt → structured JSON intent    │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2 — Planner / Orchestrator                           │
│  Model: Qwen3.5-4B (thinking mode enabled)                  │
│  Role: reasoning, task breakdown, DAG generation, tool plan │
└───────────────────────────┬─────────────────────────────────┘
                             ▼
                  [USER CONFIRM / REVISE]
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3 — Executor & Codegen Delegate                      │
│  Tool calls: read_file, write_file, list_dir, run_command   │
│  Codegen delegate → Qwen2.5-Coder-3b (precise Python code)  │
└─────────────────────────────────────────────────────────────┘
```

## Why 3 Specialized Models (Rather than 1 Monolith)

- Each model is optimized for its specific task → higher quality and precision compared to a single general model multitasking.
- Total memory footprint remains minimal because models load and execute sequentially.
- Modular: any layer can swap to alternative models or providers via adapters without rewriting the rest of the system (see `07-TechnicalDecisions.md`).

## Project Folder Structure

```text
dinggo/
│
├── docs/                    # Technical documentation & architecture guides
│
├── core/                    # 3-layer model orchestration and engine
│   ├── intent_parser.py     # Layer 1 wrapper (Gemma-SEA-LION)
│   ├── planner/             # Layer 2 wrapper (Qwen3.5-4B / Task Graph)
│   ├── executor.py          # Layer 3 — step execution & validation
│   ├── codegen.py           # Codegen delegate (Qwen2.5-Coder-3b)
│   ├── memory/              # Short-term, long-term & Contextix memory
│   └── sandbox/             # Execution sandboxing and security policies
│
├── tools/                   # Tool implementations
│   ├── file_ops.py          # read, write, list, edit, diff, search
│   └── shell_ops.py         # sandboxed run_command
│
├── cli/                     # CLI entrypoints and terminal presentation
│   ├── main.py
│   ├── interface.py         # TUI Dashboard
│   └── ui.py                # Rich console renderer
│
├── config/
│   └── models.yaml          # Layer-to-model configuration
│
├── .env                     # Environment variables (Ollama URL, model overrides)
├── .env.example
├── README.md
└── pyproject.toml
```

## Data Flow per Request

1. User input is captured in `cli/main.py` or `cli/interface.py`.
2. `core/intent_parser.py` calls Gemma-SEA-LION via Ollama API → produces structured JSON intent.
3. `core/planner/` calls Qwen3.5-4B with intent + project context (root dir, `.context/`, code graph) → generates DAG task plan.
4. `cli/ui.py` renders the plan and pauses for user confirmation.
5. Upon confirmation → `core/executor.py` executes each step:
   - Tool calls (read/write/run) are dispatched via `tools/`.
   - Steps requiring code generation delegate to `core/codegen.py` (Qwen2.5-Coder-3b), followed by semantic and syntax validation.
6. Execution summary and diffs are rendered to the console.

## Model Loading Strategy

To optimize VRAM and system memory, models are managed with Ollama (`keep_alive: 0` / eviction) during layer transitions, ensuring lightweight execution on consumer laptops and workstations.
