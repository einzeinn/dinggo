# Architecture

**Relationships:**
- **Layer 1 (Intent Parser):** Converts casual natural language requests into structured IntentSchema.
- **Layer 2 (Planner & DAG Engine):** Synthesizes step-by-step execution plans and dependency task graphs.
- **Layer 3 (Executor & Codegen Delegate):** Executes sandboxed tool calls (read/write/edit/run/search/outline) with precise code generation and semantic validation.
- **Sandboxed Runner:** Confines sub-processes, sanitizes credentials, and prevents destructive commands.
