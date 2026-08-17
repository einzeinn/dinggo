"""Unit tests for Phase 1: Spec Parser, Generator, State Machine, and Detector."""
import os
import shutil
import tempfile
import unittest

from core.spec.generator import SpecGenerator
from core.spec.parser import SpecParser
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from core.detector import ProjectDetector


class TestSpecParserAndState(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_spec_generator_and_parser(self):
        """Test generating default spec templates and parsing them into ProductSpec."""
        generator = SpecGenerator(root_dir=self.test_dir)
        created = generator.initialize_spec_directory(project_name="Inventory App")
        self.assertIn("product.md", created)
        self.assertIn("requirements.md", created)
        self.assertIn("architecture.md", created)

        # Parse the generated directory
        parser = SpecParser(root_dir=self.test_dir)
        self.assertTrue(parser.spec_exists())
        spec = parser.parse()

        self.assertEqual(spec.name, "Inventory App")
        self.assertTrue(len(spec.requirements) >= 2)
        # Check requirement IDs
        req_ids = [r.id for r in spec.requirements]
        self.assertIn("AUTH-001", req_ids)
        self.assertIn("CORE-001", req_ids)

        # Check architecture
        self.assertIn("FastAPI", spec.architecture.framework)

    def test_state_manager_lifecycle(self):
        """Test persistent state machine transitions and session resumption."""
        sm = StateManager(root_dir=self.test_dir)
        self.assertEqual(sm.state.phase, PipelinePhase.IDLE)
        self.assertFalse(sm.can_resume())

        # Transition to PLANNING
        sm.transition_to(PipelinePhase.PLANNING, PipelineStatus.IN_PROGRESS, message="Building DAG")
        self.assertEqual(sm.state.phase, PipelinePhase.PLANNING)
        self.assertEqual(sm.state.status, PipelineStatus.IN_PROGRESS)
        self.assertTrue(sm.can_resume())

        # Record task completions
        sm.record_task_completed("TASK-001")
        sm.record_task_completed("TASK-002")
        self.assertEqual(sm.state.stats.tasks_completed, 2)

        # Simulate reload from disk (new instance)
        sm_reloaded = StateManager(root_dir=self.test_dir)
        self.assertEqual(sm_reloaded.state.phase, PipelinePhase.PLANNING)
        self.assertEqual(sm_reloaded.state.stats.tasks_completed, 2)
        self.assertTrue(sm_reloaded.can_resume())

        # Complete session
        sm_reloaded.transition_to(PipelinePhase.COMPLETED, PipelineStatus.SUCCESS, message="Done")
        self.assertFalse(sm_reloaded.can_resume())

    def test_project_detector(self):
        """Test stack and provider detector."""
        # Create dummy package.json
        with open(os.path.join(self.test_dir, "package.json"), "w") as f:
            f.write('{"name": "test-app", "dependencies": {"next": "^14.0.0", "react": "^18.0.0"}}')

        detector = ProjectDetector(root_dir=self.test_dir)
        res = detector.detect_all()

        project = res["project"]
        self.assertIn("Next.js", project["frameworks"])
        self.assertIn("React", project["frameworks"])
        self.assertIn("JavaScript/TypeScript", project["languages"])

        providers = res["providers"]
        self.assertIn("ollama", providers)
        self.assertIn("codex", providers)


if __name__ == "__main__":
    unittest.main()
