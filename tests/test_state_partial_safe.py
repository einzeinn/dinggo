import os
import shutil
import tempfile
import unittest
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.planner.task_graph import TaskGraphSchema, TaskNode
from core.orchestrator.scheduler import TaskScheduler
from core.workers.base_worker import BaseWorker, ExecutionRecord


class DummyWorker(BaseWorker):
    def __init__(self, root_dir=".", succeed_ids=None):
        super().__init__(root_dir=root_dir)
        self.succeed_ids = succeed_ids or set()
        self.executed_tasks = []

    def execute_task(self, task, spec=None, context=None):
        self.executed_tasks.append(task.id)
        if task.id in self.succeed_ids:
            return ExecutionRecord(
                task_id=task.id,
                worker_type=task.worker_type,
                status="completed",
                output_summary=f"Task {task.id} succeeded"
            )
        else:
            return ExecutionRecord(
                task_id=task.id,
                worker_type=task.worker_type,
                status="failed",
                error=f"Task {task.id} failed intentionally"
            )


class TestStatePartialSafe(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_partial_safe_persistence(self):
        # Record task 1 as completed
        self.state_mgr.record_task_completed("task-1")
        self.assertTrue(self.state_mgr.is_task_completed("task-1"))
        self.assertEqual(self.state_mgr.state.completed_task_ids, ["task-1"])

        # Record task 2 as failed
        self.state_mgr.record_task_failed("task-2", error="Syntax error in module")
        self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.FAILED, "Task 2 failed")

        # Reload from disk
        reloaded_mgr = StateManager(root_dir=self.temp_dir)
        # Task 1 must NOT be reset!
        self.assertIn("task-1", reloaded_mgr.state.completed_task_ids)
        self.assertIn("task-2", reloaded_mgr.state.failed_task_ids)
        self.assertEqual(reloaded_mgr.state.task_errors.get("task-2"), "Syntax error in module")
        self.assertTrue(reloaded_mgr.can_resume())

    def test_pending_tasks_calculation(self):
        self.state_mgr.record_task_completed("task-1")
        self.state_mgr.record_task_completed("task-2")
        all_ids = ["task-1", "task-2", "task-3", "task-4"]

        pending = self.state_mgr.get_pending_task_ids(all_ids)
        self.assertEqual(pending, ["task-3", "task-4"])

    def test_scheduler_skips_already_completed_tasks_on_resume(self):
        # Create a DAG with 3 tasks: t1 -> t2 -> t3
        tasks = [
            TaskNode(id="t1", title="Task 1", description="Implement DB layer", worker_type="backend", depends_on=[]),
            TaskNode(id="t2", title="Task 2", description="Implement auth service", worker_type="backend", depends_on=["t1"]),
            TaskNode(id="t3", title="Task 3", description="Add auth tests", worker_type="backend", depends_on=["t2"]),
        ]
        graph = TaskGraphSchema(project_name="test-proj", tasks=tasks)

        # Pre-populate state with t1 completed
        self.state_mgr.record_task_completed("t1")

        scheduler = TaskScheduler(root_dir=self.temp_dir, state_manager=self.state_mgr)

        # Monkey patch worker resolver to return our DummyWorker
        dummy_worker = DummyWorker(root_dir=self.temp_dir, succeed_ids={"t2", "t3"})
        import core.orchestrator.scheduler as sched_mod
        orig_get_worker = sched_mod.get_worker_for_type
        sched_mod.get_worker_for_type = lambda wtype, **kwargs: dummy_worker

        try:
            res = scheduler.execute_graph(graph)
            self.assertTrue(res["success"])
            # t1 should NOT have been re-executed! Only t2 and t3
            self.assertEqual(dummy_worker.executed_tasks, ["t2", "t3"])
            self.assertEqual(set(self.state_mgr.state.completed_task_ids), {"t1", "t2", "t3"})
        finally:
            sched_mod.get_worker_for_type = orig_get_worker


if __name__ == "__main__":
    unittest.main()
