# 07 - Technical Decisions

Each decision is structured as: **Decision → Rationale → Alternatives Considered → When to Revisit.**

---

## TD-001: Ollama as Local Model Runtime

**Decision:** Use Ollama to serve all local LLMs via REST API.

**Rationale:** Standardized local REST API, robust model lifecycle management (`pull`, `stop`, `list`, `ps`), cross-platform support without requiring manual `llama.cpp` compilation.

**Alternatives:** Direct `llama.cpp` binary binding, LM Studio.

**Revisit if:** Specific advanced features (e.g. custom speculative decoding or specialized batching pipelines) become necessary.

---

## TD-002: 3-Layer Specialized Model Orchestration

**Decision:** Separate core responsibilities across 3 specialized models (Intent Parsing, Planning/DAG, Codegen) rather than a single general-purpose model.

**Rationale:** Small models (<4B) trained specifically for a single domain (such as `Qwen2.5-Coder` for code synthesis) consistently outperform general models of the same parameter scale on specialized tasks. Tool calling and structured schema generation are sensitive to domain tuning.

**Alternatives:** Single large model (e.g. Llama 3.1 8B) for all tasks — simpler architecture but requires more memory and yields lower per-task precision.

**Revisit if:** An all-in-one <4B model emerges that achieves equal or better precision across all 3 phases simultaneously.

---

## TD-003: Model Selection per Layer

| Layer | Model | Rationale |
| :--- | :--- | :--- |
| **Intent Parsing** | Gemma-SEA-LION-V4.5-E2B-IT | Excellent casual multilingual/SEA language understanding, fast inference. |
| **Planner / DAG** | Qwen3.5-4B | State-of-the-art tool-calling & reasoning in the <4B class, thinking mode, 262K context. |
| **Codegen** | Qwen2.5-Coder-3b | Code generation specialist, lightweight, clean syntax generation. |
| **Fallback** | Llama 3.1 8B | Deep reasoning for heavy offline batch tasks. |

**Revisit if:** New lightweight models demonstrate higher benchmark scores on task graph generation and code synthesis.

---

## TD-004: Sequential Model Loading (Memory Safety)

**Decision:** Models transition sequentially per active lifecycle phase rather than remaining concurrently resident in VRAM/RAM.

**Rationale:** Standard consumer laptops and workstations (16GB RAM, integrated graphics) risk Out-Of-Memory (OOM) crashes if 3 models (4.9GB + 4GB + 2GB) run concurrently alongside OS processes.

**Alternatives:** Concurrent residency — feasible on high-end systems with dedicated GPU VRAM (>=16GB).

**Revisit if:** User environment hardware is upgraded or switching latency becomes a critical bottleneck.

---

## TD-005: Python as Primary Implementation Language

**Decision:** Core orchestrator, CLI, tools, and test suites are written in Python.

**Rationale:** Rich CLI/TUI ecosystem (`rich`, `prompt_toolkit`, `pydantic`, `pytest`), strong native AST parsing capabilities for code validation, and high extensibility.

---

## TD-006: `rich` + `prompt_toolkit` for Terminal Interface

**Decision:** Use `rich` for formatted rendering (panels, syntax highlighting, diffs, live status timers) and `prompt_toolkit` for interactive prompt history and autocomplete.

**Rationale:** Industry standard for developer CLI tools (similar to Claude Code and Codex CLI), stable, cross-platform, and fully customizable.

---

## TD-007: Dynamic Configuration via `.env` and Settings

**Decision:** Externalize runtime configurations (Ollama base URL, model overrides, thread allocations) to `.env` and Dinggo Settings rather than hardcoded constants.

**Rationale:** Enables zero-code model swapping and environment-specific overrides.
