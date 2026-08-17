# RFC-011: Direct CLI Commands, CI/CD Pipeline & End-to-End Automation

## Status
**Proposed & Accepted**

## 1. Summary
RFC-011 defines the architecture for Dinggo's **Direct CLI Command Interface**, **CI/CD Non-Interactive Mode**, and unified **Product Factory Pipeline (`ProductFactoryPipeline`)**.
It enables Dinggo to be executed both as an interactive visual TUI tool and as an automated headless CLI/CI engine suitable for GitHub Actions, GitLab CI, and programmatic invocation.

---

## 2. Direct CLI Subcommand Dispatcher (`cli/main.py`)

Dinggo supports both interactive mode (`dinggo`, `dinggo interface`, `dinggo wizard`) and direct subcommand execution:

| Subcommand | Description | Flags |
|---|---|---|
| `dinggo` / `dinggo interface` | Launches interactive TUI shell | `--dir` |
| `dinggo init [path]` | Scaffolds `spec/` and `dinggo.yaml` | `--non-interactive` |
| `dinggo plan [path]` | Generates Task Graph DAG | `--non-interactive`, `--json` |
| `dinggo build [path]` | Runs full end-to-end factory pipeline | `--non-interactive`, `--ci`, `--auto-approve` |
| `dinggo test [path]` | Executes test runner and repair engine | `--max-attempts` |
| `dinggo review [path]` | Executes 4-quadrant code audit | `--json` |
| `dinggo status [path]` | Displays session state & pipeline stats | `--json` |
| `dinggo resume [path]` | Resumes saved session from `.dinggo/state.yaml` | `--non-interactive` |

---

## 3. Product Factory Pipeline (`core/factory.py`)

Unified orchestration engine connecting all 8 phases:

```text
SPECIFICATION (Phase 1)
      │
      ▼
PLANNER DAG (Phase 3)
      │
      ▼
APPROVAL GATE 1 (Plan Review)
      │
      ▼
MULTI-WORKER IMPLEMENTATION (Phase 4)
      │
      ▼
MULTI-TIER TESTING & REPAIR (Phase 5)
      │
      ▼
APPROVAL GATE 2 (Validation Review)
      │
      ▼
PRODUCTION BUILD & PACKAGING (Phase 6)
      │
      ▼
INDEPENDENT CODE AUDIT (Phase 7)
      │
      ▼
APPROVAL GATE 3 (Export Review)
      │
      ▼
COMPLETED RELEASE ARTIFACTS (dist/)
```

---

## 4. CI/CD & Headless Exit Codes
- `0`: Success (Pipeline completed, tests passed, build exported).
- `1`: Pipeline failure (Unmet dependencies, test failure after max repair attempts, audit rejected).
- `2`: Configuration or runtime execution error.

---

## 5. Verification & Test Strategy
- Unit tests verifying direct CLI subcommands (`init`, `plan`, `build`, `test`, `review`, `status`, `resume`).
- End-to-end integration test running `ProductFactoryPipeline` from `spec/` generation to `dist/` export in headless mode.
