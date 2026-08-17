"""Unit tests for Phase 4: Multi-Worker Implementation Engine & Live Dashboard."""
import io
import os
import shutil
import tempfile
import unittest
from rich.console import Console

from core.planner.task_graph import TaskNode, TaskGraphSchema
from core.spec.models import ProductSpec, RequirementItem
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.workers import (
    get_worker_for_type,
    InfraWorker,
    DatabaseWorker,
    BackendWorker,
    FrontendWorker,
    IntegrationWorker,
    ExecutionRecord
)
from core.orchestrator.scheduler import TaskScheduler
from cli.execution_view import LiveExecutionDashboard


class TestExecutionWorkersAndScheduler(unittest.TestCase):
    def setUp(self):
        os.environ["DINGGO_TEST_MODE"] = "1"
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_specialized_workers_execution(self):
        """Test each specialized worker produces expected files and records."""
        # 1. InfraWorker
        t_infra = TaskNode(id="TASK-001", title="Setup", description="scaffold", worker_type="infra", target_files=["config.yaml"])
        w_infra = get_worker_for_type("infra", root_dir=self.test_dir)
        rec_infra = w_infra.execute_task(t_infra)
        self.assertEqual(rec_infra.status, "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "config.yaml")))

        # 2. DatabaseWorker
        t_db = TaskNode(id="TASK-002", title="DB Schema", description="models", worker_type="database", target_files=["models.py"])
        w_db = get_worker_for_type("database", root_dir=self.test_dir)
        rec_db = w_db.execute_task(t_db)
        self.assertEqual(rec_db.status, "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "models.py")))

        # 3. BackendWorker
        t_be = TaskNode(id="TASK-003", title="Auth API", description="auth", requirement_id="AUTH-001", worker_type="backend", target_files=["auth.py"])
        w_be = get_worker_for_type("backend", root_dir=self.test_dir)
        rec_be = w_be.execute_task(t_be)
        self.assertEqual(rec_be.status, "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "auth.py")))

        # 4. FrontendWorker
        t_fe = TaskNode(id="TASK-004", title="UI View", description="ui", requirement_id="AUTH-001", worker_type="frontend", target_files=["view.tsx"])
        w_fe = get_worker_for_type("frontend", root_dir=self.test_dir)
        rec_fe = w_fe.execute_task(t_fe)
        self.assertEqual(rec_fe.status, "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "view.tsx")))

        # 5. IntegrationWorker
        t_in = TaskNode(id="TASK-005", title="Wiring", description="wire", worker_type="integration", target_files=["main.py"])
        w_in = get_worker_for_type("integration", root_dir=self.test_dir)
        rec_in = w_in.execute_task(t_in)
        self.assertEqual(rec_in.status, "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "main.py")))

    def test_task_scheduler_full_dag(self):
        """Test scheduler executing an entire multi-task DAG in dependency order."""
        t1 = TaskNode(id="TASK-001", title="Scaffold", description="1", worker_type="infra", target_files=["init.txt"], depends_on=[])
        t2 = TaskNode(id="TASK-002", title="DB Models", description="2", worker_type="database", target_files=["db.txt"], depends_on=["TASK-001"])
        t3 = TaskNode(id="TASK-003", title="Backend API", description="3", worker_type="backend", target_files=["api.txt"], depends_on=["TASK-002"])

        graph = TaskGraphSchema(project_name="Scheduler App", tasks=[t3, t1, t2])
        scheduler = TaskScheduler(root_dir=self.test_dir, state_manager=self.state_mgr)

        res = scheduler.execute_graph(graph)
        self.assertTrue(res["success"])
        self.assertEqual(res["completed_tasks"], 3)
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.TESTING)
        self.assertEqual(self.state_mgr.state.stats.tasks_completed, 3)

        # Check all files exist
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "init.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "db.txt")))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "api.txt")))

    def test_live_execution_dashboard(self):
        """Test dashboard executing plan with callbacks."""
        t1 = TaskNode(id="TASK-001", title="Scaffold", description="1", worker_type="infra", target_files=["scaffold.txt"], depends_on=[])
        graph = TaskGraphSchema(project_name="Dashboard App", tasks=[t1])

        dashboard = LiveExecutionDashboard(root_dir=self.test_dir, console=self.console, state_manager=self.state_mgr)
        success = dashboard.execute_plan(graph)
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
