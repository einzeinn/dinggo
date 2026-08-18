import os
import shutil
import tempfile
import unittest
from core.memory.contextix_adapter import ContextixAdapter
from core.memory.project_context import ProjectContext
from core.planner.task_graph import TaskGraphSchema, TaskNode
from core.state.state_manager import StateManager


class TestContextixRecovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.context = ProjectContext(working_dir=self.temp_dir)
        self.adapter = ContextixAdapter(self.context)
        self.state_mgr = StateManager(root_dir=self.temp_dir)

        # Setup mock .context memory
        ctx_dir = os.path.join(self.temp_dir, ".context")
        os.makedirs(ctx_dir, exist_ok=True)
        with open(os.path.join(ctx_dir, "context.yaml"), "w", encoding="utf-8") as f:
            f.write(
                "project:\n"
                "  name: RecoveryApp\n"
                "constraints:\n"
                "  - 'All endpoints must use JWT auth'\n"
                "  - 'Never use raw SQL queries'\n"
                "decisions:\n"
                "  - what: 'Use FastAPI with Pydantic'\n"
                "    why: 'Fast typing and automatic docs'\n"
            )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_build_recovery_context_targeted_state(self):
        # Create DAG
        tasks = [
            TaskNode(id="task-1", title="Setup DB", description="Setup database schema", worker_type="backend", depends_on=[]),
            TaskNode(id="task-2", title="Create Auth Router", description="Build auth router", worker_type="backend", depends_on=["task-1"], target_files=["src/auth.py"]),
            TaskNode(id="task-3", title="Add User Tests", description="Unit tests for user auth", worker_type="integration", depends_on=["task-2"]),
        ]
        graph = TaskGraphSchema(project_name="RecoveryApp", tasks=tasks)

        # State has task-1 completed, task-2 failed
        self.state_mgr.record_task_completed("task-1")
        self.state_mgr.record_task_failed("task-2", error="ImportError: No module named 'jose'")

        recovery_prompt = self.adapter.build_recovery_context(
            failed_task_id="task-2",
            task_graph=graph,
            state=self.state_mgr.state,
            error_info="ImportError: No module named 'jose'"
        )

        self.assertIn("RECOVERY CONTEXT", recovery_prompt)
        self.assertIn("Completed Tasks (Preserved): task-1", recovery_prompt)
        self.assertIn("Task 'task-2' (Create Auth Router)", recovery_prompt)
        self.assertIn("ImportError: No module named 'jose'", recovery_prompt)
        self.assertIn("All endpoints must use JWT auth", recovery_prompt)
        self.assertIn("Do not modify or redo already completed tasks", recovery_prompt)


if __name__ == "__main__":
    unittest.main()
