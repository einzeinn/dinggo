# 08 - Design (CLI UX & Terminal Visuals)

## Reference

Inspired by Codex CLI and Claude Code, featuring distinctive layer status badges (transparency of internal reasoning) and rich interactive components.

## Design Principles

1. **Transparent by Default** — The user always knows which lifecycle phase is currently executing (Intent Parsing / Planning / Execution / Validation) and which model is active.
2. **Clear Confirmation Gates** — Plans are rendered in distinct structured panels with clear confirmation prompts prior to state changes.
3. **Concise yet Informative** — Output does not flood the terminal buffer; large content (file reads, outlines) is cleanly summarized or collapsed.

## Visual Elements

### Startup
- ASCII banner with project version
- Displays active workspace directory and model mapping

### Active Layer Indicators
Icons and distinct styling for each execution layer:

| Layer | Icon | Description |
| :--- | :--- | :--- |
| **Layer 1: Intent Parsing** (Gemma-SEA-LION) | 🗣️ | "Parsing intent and target instruction..." |
| **Layer 2: Planning & DAG** (Qwen3.5-4B) | 🧠 | "Constructing execution plan..." |
| **Layer 3: Codegen** (Qwen2.5-Coder) | ⚡ | "Generating code..." |
| **Layer 3: Tool Execution** | 🔧 | "Executing step: <action_type>" |
| **Layer 4: Validator** | 🛡️ | "Validating syntax & semantics..." |

### Plan Display
- Numbered table: step number, action type, target file/command, and description.
- Panel with rounded borders (`rich.Panel`).
- Confirmation prompt below the plan: `[Y] Execute   [R] Revise   [N] Cancel`.

### Diff View (Prior to Applying File Modifications)
- Green (additions) / red (deletions), standard unified diff format.
- Rendered on a per-file basis.

### Execution Progress
- Live ticking spinner per active step (`ui.live_status`).
- Clear step results: success (✓), response only (○), or failure (✗).

### Error Handling & Rollback
- Errors are highlighted in dedicated panels with details and automatic atomic rollback on failure.

## UI Technology Stack

- `rich` — Panels, syntax highlighting, diff rendering, live status timers, markdown formatting.
- `prompt_toolkit` — Interactive user prompts, command history (↑/↓), and slash command autocomplete.
