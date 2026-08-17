"""Directed Acyclic Graph (DAG) Task Graph Schema & Schedulers for Dinggo Product Factory."""
from typing import List, Dict, Any, Optional, Literal, Set
from collections import defaultdict, deque
from pydantic import BaseModel, Field, model_validator


class TaskNode(BaseModel):
    """Represents a discrete task node in the execution DAG."""
    id: str = Field(description="Unique Task ID, e.g. TASK-001")
    title: str = Field(description="Short human-readable summary of the task")
    description: str = Field(description="Detailed execution instruction for worker")
    requirement_id: Optional[str] = Field(default=None, description="Linked Requirement ID, e.g. AUTH-001")
    worker_type: Literal["backend", "frontend", "database", "infra", "integration", "general"] = "backend"
    target_files: List[str] = Field(default_factory=list, description="Target files created or modified")
    depends_on: List[str] = Field(default_factory=list, description="IDs of tasks that must complete before this task")
    test_ids: List[str] = Field(default_factory=list, description="Associated test identifiers")
    status: Literal["pending", "in_progress", "completed", "failed", "skipped"] = "pending"


class TaskGraphSchema(BaseModel):
    """Master execution DAG containing ordered task nodes linked to requirements."""
    project_name: str = "Unnamed Project"
    architecture: str = "FastAPI + React"
    database: str = "SQLite / PostgreSQL"
    requirements_coverage: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Mapping of Requirement ID to list of Task IDs satisfying it"
    )
    tasks: List[TaskNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dag_integrity(self):
        """Validate that task IDs are unique and no circular dependencies exist."""
        task_ids = set()
        for t in self.tasks:
            if t.id in task_ids:
                raise ValueError(f"Duplicate task ID detected: {t.id}")
            task_ids.add(t.id)

        # Validate dependency existence
        for t in self.tasks:
            for dep in t.depends_on:
                if dep not in task_ids:
                    raise ValueError(f"Task '{t.id}' depends on non-existent task '{dep}'")

        # Validate cycle absence
        if self.has_cycle():
            raise ValueError("Circular dependency cycle detected in Task Graph DAG!")

        # Auto-compute requirement coverage if empty
        if not self.requirements_coverage:
            coverage = defaultdict(list)
            for t in self.tasks:
                if t.requirement_id:
                    coverage[t.requirement_id].append(t.id)
            self.requirements_coverage = {k: sorted(v) for k, v in coverage.items()}

        return self

    def has_cycle(self) -> bool:
        """Check if graph contains any circular dependency cycles."""
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        task_ids = {t.id for t in self.tasks}

        for t in task_ids:
            in_degree[t] = 0

        for t in self.tasks:
            for dep in t.depends_on:
                adj[dep].append(t.id)
                in_degree[t.id] += 1

        queue = deque([t for t in task_ids if in_degree[t] == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return visited_count != len(task_ids)

    def get_topological_order(self) -> List[TaskNode]:
        """Return tasks sorted in valid topological dependency execution order."""
        task_map = {t.id: t for t in self.tasks}
        adj = defaultdict(list)
        in_degree = {t.id: 0 for t in self.tasks}

        for t in self.tasks:
            for dep in t.depends_on:
                adj[dep].append(t.id)
                in_degree[t.id] += 1

        # Use priority queue or deterministic sort order for tasks at same tier
        queue = deque(sorted([t_id for t_id, deg in in_degree.items() if deg == 0]))
        ordered: List[TaskNode] = []

        while queue:
            t_id = queue.popleft()
            ordered.append(task_map[t_id])
            for neighbor in sorted(adj[t_id]):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return ordered

    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """Find a task node by ID."""
        for t in self.tasks:
            if t.id.upper() == task_id.upper():
                return t
        return None
