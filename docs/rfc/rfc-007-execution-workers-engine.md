# RFC-007: Multi-Worker Execution Engine & Live Dashboard

## Status
**Proposed & Accepted**

## 1. Summary
RFC-007 defines the architecture for Dinggo's **Multi-Worker Implementation Engine** and **Live Execution Dashboard**.
It replaces single-script execution with specialized domain workers orchestrated across a task dependency graph (DAG), providing real-time visual progress monitoring and execution records.

---

## 2. Multi-Worker Architecture (`core/workers/`)

```text
                    DINGGO ORCHESTRATOR
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
      Backend Worker   Frontend Worker   DB Worker
       (API/Logic)       (UI/Client)     (Schema/ORM)
            │                │                │
            └────────────────┼────────────────┘
                             ▼
                     Integration Worker
```

### Worker Interface (`core/workers/base_worker.py`)
```python
class ExecutionRecord(BaseModel):
    task_id: str
    requirement_id: Optional[str] = None
    worker_type: str
    status: Literal["completed", "failed", "skipped"]
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    output_summary: str = ""
    error: Optional[str] = None
    elapsed_seconds: float = 0.0

class BaseWorker(ABC):
    @abstractmethod
    def execute_task(self, task: TaskNode, spec: ProductSpec, context: Optional[str] = None) -> ExecutionRecord:
        pass
```

### Specialized Workers
1. **BackendWorker**: Generates server logic, services, auth endpoints, controllers.
2. **FrontendWorker**: Generates UI components, styles, layouts, client state.
3. **DatabaseWorker**: Generates data models, ORM schemas, migration scripts.
4. **InfraWorker**: Generates project configurations, environment setup, package files.
5. **IntegrationWorker**: Connects backend routes to frontend client views.

---

## 3. DAG Task Scheduler (`core/orchestrator/scheduler.py`)

The scheduler manages task resolution and execution order:
- Iterates over topological sort order.
- Dispatches task to corresponding worker based on `worker_type`.
- Updates persistent state in `.dinggo/state.yaml` after each task completion.
- Records output artifacts and files.

---

## 4. Live Execution Dashboard (`cli/execution_view.py`)

The TUI provides real-time progress feedback during execution:

```text
╭──────────────────────────────────────────╮
│             DINGGO EXECUTION             │
├──────────────────────────────────────────┤
│ Project:  Inventory App                  │
│ Phase:    IMPLEMENTATION                 │
│ Progress: ██████████████░░░░ 72% (60/83) │
│                                          │
│ Active:   TASK-047                       │
│ Title:    Implement inventory dashboard  │
│ Worker:   [Frontend Agent]               │
│ Target:   src/inventory/dashboard.tsx    │
│                                          │
│ Controls: [P] Pause  [L] Logs  [C] Cancel│
╰──────────────────────────────────────────╯
```

---

## 5. Verification & Test Strategy
- Unit tests verifying worker dispatching based on `task.worker_type`.
- Unit tests verifying `ExecutionRecord` creation and file tracking.
- Unit tests for the `TaskScheduler` executing a complete DAG.
- Tests for execution dashboard progress calculation and status updates.
