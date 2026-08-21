# 01 - Vision

## Problem Statement

Existing agentic coding tools (Claude Code, Codex, Cursor CLI, etc.) are powerful, but they depend entirely on cloud APIs — requiring active internet connection, per-token costs, and transmitting private code/prompts to third-party servers. For personal experimentation, hackathons, or sensitive confidential work, this creates significant friction (cost, latency, and data privacy concerns).

On the other hand, modern open-weight models under 4B parameters are now capable of structured tool-calling and reasoning (see `07-TechnicalDecisions.md`). The workflow of **"reason → plan → confirm → execute"** can now run 100% locally on standard consumer hardware.

## Vision

**Dinggo** is a personal CLI IDE and Product Factory that runs entirely locally (offline-first), allowing developers to navigate to any project root folder, provide natural language instructions, and receive:

1. Accurate intent understanding
2. An explicit, human-reviewable execution plan prior to execution
3. Precise code execution (primarily Python) via sandboxed tool-calling

all without relying on paid APIs or internet connectivity, powered by a multi-model orchestration pipeline where small, specialized models handle distinct tasks.

## Target Audience & Use Cases

Personal use — developer workflow automation:
- Hackathon projects (forcing function for rapid end-to-end delivery)
- AI tooling experiments, backend development, desktop applications
- Privacy-sensitive and offline-first workflows where code must remain strictly on-device

## Non-Goals (v1)

- **Not** a multi-user / SaaS product
- **Not** an all-in-one replacement for large cloud models on extreme reasoning tasks — Dinggo is optimized for medium-scale tasks that can be broken down into structured sub-tasks
- **Not** a visual GUI IDE/editor — strictly a CLI/TUI terminal tool
- **Not** targeting multi-language runtimes simultaneously in v1 — primary focus is Python

## Core Principles

1. **Local-first** — all models execute via local Ollama instances on-device
2. **Transparent** — execution plans are always displayed and confirmed prior to performing state-changing operations
3. **Modular & Swappable** — model backends and adapters can be updated without rewriting the core engine
4. **Documentation before massive scope** — see `RFC-001.md`

## Definition of Success (v1)

- Navigate to any project workspace root, run `dinggo`, enter a prompt, and receive a coherent execution plan
- Upon confirmation, execution (file I/O, search, commands) succeeds without fatal unhandled errors
- 3-model orchestration (intent parser → planner/DAG → codegen) executes seamlessly within 16GB RAM constraints
