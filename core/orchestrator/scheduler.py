"""DAG Task Scheduler & Orchestrator for Dinggo Product Factory."""
import time
from typing import List, Dict, Any, Optional, Callable
from core.planner.task_graph import TaskGraphSchema, TaskNode
from core.spec.models import ProductSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.workers import get_worker_for_type, ExecutionRecord


class TaskScheduler:
    """Orchestrates execution of TaskGraph DAG nodes across specialized workers."""

    def __init__(
        self,
        root_dir: str = ".",
        state_manager: Optional[StateManager] = None,
        ollama_client: Optional[Any] = None
    ):
        self.root_dir = root_dir
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.client = ollama_client
        self.execution_records: List[ExecutionRecord] = []

    def execute_graph(
        self,
        graph: TaskGraphSchema,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None,
        on_task_start: Optional[Callable[[TaskNode, int, int], None]] = None,
        on_task_finish: Optional[Callable[[TaskNode, ExecutionRecord, int, int], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes all tasks in the DAG in topological dependency order.
        Returns execution results dictionary.
        """
        self.state_mgr.transition_to(PipelinePhase.IMPLEMENTING, PipelineStatus.IN_PROGRESS, "Executing task graph DAG", can_resume=True)
        topological_tasks = graph.get_topological_order()
        total_tasks = len(topological_tasks)
        completed_ids = set(self.state_mgr.get_completed_task_ids())

        start_time = time.time()

        for idx, task in enumerate(topological_tasks, start=1):
            # If task was already completed in a previous or partial run, preserve state and skip re-executing
            if task.id in completed_ids:
                task.status = "completed"
                # Add existing synthetic or preserved record if not already tracked
                if not any(r.task_id == task.id for r in self.execution_records):
                    self.execution_records.append(ExecutionRecord(
                        task_id=task.id,
                        requirement_id=task.requirement_id,
                        worker_type=task.worker_type,
                        status="completed",
                        output_summary=f"Task {task.id} already completed (partial-safe cache preserved)."
                    ))
                continue

            # Check dependency satisfaction
            for dep_id in task.depends_on:
                if dep_id not in completed_ids:
                    task.status = "skipped"
                    rec = ExecutionRecord(
                        task_id=task.id,
                        requirement_id=task.requirement_id,
                        worker_type=task.worker_type,
                        status="skipped",
                        error=f"Unmet dependency: '{dep_id}' was not completed."
                    )
                    self.execution_records.append(rec)
                    self.state_mgr.record_task_failed(task.id, rec.error)
                    self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.FAILED, f"Task {task.id} skipped due to unmet dependency {dep_id}", can_resume=True)
                    return {
                        "success": False,
                        "failed_task_id": task.id,
                        "records": self.execution_records,
                        "error": rec.error
                    }

            # Notify task start
            task.status = "in_progress"
            self.state_mgr.state.session.active_task_id = task.id
            self.state_mgr.save()

            if on_task_start:
                on_task_start(task, idx, total_tasks)

            # Delegate to specialized worker
            worker = get_worker_for_type(task.worker_type, root_dir=self.root_dir, ollama_client=self.client)
            record = worker.execute_task(task, spec=spec, context=context)

            self.execution_records.append(record)

            if record.status == "completed":
                task.status = "completed"
                completed_ids.add(task.id)
                self.state_mgr.record_task_completed(task.id)
            else:
                task.status = "failed"
                self.state_mgr.record_task_failed(task.id, record.error or "Execution failed")
                self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.FAILED, f"Task {task.id} failed: {record.error}", can_resume=True)
                if on_task_finish:
                    on_task_finish(task, record, idx, total_tasks)
                return {
                    "success": False,
                    "failed_task_id": task.id,
                    "records": self.execution_records,
                    "error": record.error
                }

            # Notify task finish
            if on_task_finish:
                on_task_finish(task, record, idx, total_tasks)

        elapsed = round(time.time() - start_time, 2)
        self.state_mgr.transition_to(PipelinePhase.TESTING, PipelineStatus.IN_PROGRESS, "All implementation tasks completed, ready for testing", can_resume=True)

        return {
            "success": True,
            "total_tasks": total_tasks,
            "completed_tasks": len(completed_ids),
            "records": self.execution_records,
            "elapsed_seconds": elapsed
        }
