"""Unit tests for Phase 3: Spec-Driven Task Graph Planner and Approval Gate 1."""
import io
import unittest
from rich.console import Console
from pydantic import ValidationError

from core.planner.task_graph import TaskNode, TaskGraphSchema
from core.planner import Planner
from core.spec.models import ProductSpec, RequirementItem, ArchitectureSpec
from cli.gates.plan_review import PlanReviewGate


class TestTaskGraphPlanner(unittest.TestCase):
    def setUp(self):
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def test_valid_dag_and_topological_sort(self):
        """Test creating a valid DAG and verifying topological sort execution order."""
        t1 = TaskNode(id="TASK-001", title="Init Setup", description="scaffold", worker_type="infra", depends_on=[])
        t2 = TaskNode(id="TASK-002", title="DB Models", description="db", worker_type="database", depends_on=["TASK-001"])
        t3 = TaskNode(id="TASK-003", title="Auth API", description="auth", requirement_id="AUTH-001", worker_type="backend", depends_on=["TASK-002"])
        t4 = TaskNode(id="TASK-004", title="Auth UI", description="ui", requirement_id="AUTH-001", worker_type="frontend", depends_on=["TASK-003"])

        graph = TaskGraphSchema(
            project_name="Inventory App",
            architecture="FastAPI + React",
            database="PostgreSQL",
            tasks=[t4, t2, t1, t3]  # Out of order on purpose
        )

        self.assertFalse(graph.has_cycle())
        ordered = graph.get_topological_order()
        ordered_ids = [t.id for t in ordered]

        # Verify TASK-001 is first, followed by TASK-002, TASK-003, TASK-004
        self.assertEqual(ordered_ids, ["TASK-001", "TASK-002", "TASK-003", "TASK-004"])
        # Check requirement coverage mapping
        self.assertIn("AUTH-001", graph.requirements_coverage)
        self.assertEqual(graph.requirements_coverage["AUTH-001"], ["TASK-003", "TASK-004"])

    def test_cycle_detection(self):
        """Test that circular dependencies are detected and rejected by Pydantic validator."""
        t1 = TaskNode(id="TASK-001", title="Task 1", description="1", depends_on=["TASK-002"])
        t2 = TaskNode(id="TASK-002", title="Task 2", description="2", depends_on=["TASK-001"])

        with self.assertRaises(ValidationError) as ctx:
            TaskGraphSchema(
                project_name="Cycle App",
                architecture="Node",
                database="None",
                tasks=[t1, t2]
            )
        self.assertIn("Circular dependency cycle detected", str(ctx.exception))

    def test_invalid_dependency_id(self):
        """Test that referencing a non-existent task ID fails validation."""
        t1 = TaskNode(id="TASK-001", title="Task 1", description="1", depends_on=["TASK-999"])
        with self.assertRaises(ValidationError) as ctx:
            TaskGraphSchema(tasks=[t1])
        self.assertIn("depends on non-existent task", str(ctx.exception))

    def test_planner_create_product_task_graph_fallback(self):
        """Test Planner create_product_task_graph deterministic fallback from ProductSpec when Ollama is unavailable."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.is_available.return_value = False

        spec = ProductSpec(
            name="Test Inventory System",
            architecture=ArchitectureSpec(framework="FastAPI + Svelte", database="PostgreSQL"),
            requirements=[
                RequirementItem(id="INV-001", title="Item Creation", description="Create inventory items", priority="high", category="functional"),
                RequirementItem(id="AUTH-001", title="User Login", description="Secure JWT authentication", priority="critical", category="security")
            ]
        )

        planner = Planner(ollama_client=mock_client)
        res = planner.create_product_task_graph(spec)
        self.assertTrue(res["success"])
        self.assertEqual(res["source"], "deterministic_fallback")

        graph: TaskGraphSchema = res["graph"]
        self.assertEqual(graph.project_name, "Test Inventory System")
        self.assertIn("FastAPI", graph.architecture)
        self.assertTrue(len(graph.tasks) >= 4)

        # Check topological sorting works on generated graph
        ordered = graph.get_topological_order()
        self.assertEqual(len(ordered), len(graph.tasks))

    def test_planner_create_product_task_graph_llm(self):
        """Test Planner create_product_task_graph with mocked LLM response."""
        from unittest.mock import MagicMock
        import json

        mock_llm_json = {
            "project_name": "Mock App",
            "architecture": "Next.js + FastAPI",
            "database": "PostgreSQL",
            "tasks": [
                {"id": "TASK-001", "title": "Scaffold", "description": "init", "requirement_id": None, "worker_type": "infra", "target_files": ["README.md"], "depends_on": []},
                {"id": "TASK-002", "title": "Auth", "description": "jwt", "requirement_id": "AUTH-001", "worker_type": "backend", "target_files": ["auth.py"], "depends_on": ["TASK-001"]}
            ]
        }

        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.generate.return_value = {
            "success": True,
            "response": json.dumps(mock_llm_json)
        }

        spec = ProductSpec(name="Mock App", requirements=[RequirementItem(id="AUTH-001", description="Auth")])
        planner = Planner(ollama_client=mock_client)
        res = planner.create_product_task_graph(spec)
        self.assertTrue(res["success"])
        self.assertEqual(res["source"], "llm")
        self.assertEqual(len(res["graph"].tasks), 2)

    def test_plan_review_gate(self):
        """Test PlanReviewGate non-interactive confirmation."""
        t1 = TaskNode(id="TASK-001", title="Setup", description="scaffold", worker_type="infra")
        graph = TaskGraphSchema(project_name="Test Gate", tasks=[t1])

        gate = PlanReviewGate(console=self.console)
        approved, feedback = gate.review_and_confirm(graph, non_interactive=True)
        self.assertTrue(approved)
        self.assertIsNone(feedback)


if __name__ == "__main__":
    unittest.main()
