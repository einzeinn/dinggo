"""End-to-end integration tests for Product Factory Pipeline and CLI subcommands."""
import io
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock
from rich.console import Console

from core.factory import ProductFactoryPipeline
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class TestProductFactoryPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_pipeline_e2e_headless_run(self):
        """Test full 8-phase pipeline running end-to-end to export completion."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = False

        pipeline = ProductFactoryPipeline(
            root_dir=self.test_dir,
            console=self.console,
            state_manager=self.state_mgr,
            ollama_client=mock_client,
            non_interactive=True
        )

        success = pipeline.run_pipeline(auto_approve=True)
        self.assertTrue(success)

        # 1. Check spec files generated
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, "spec")))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "dinggo.yaml")))

        # 2. Check build artifacts in dist/
        dist_dir = os.path.join(self.test_dir, "dist")
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "metadata.json")))
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "bundle.zip")))
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "Dockerfile")))

        # 3. Check final state machine status
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.COMPLETED)
        self.assertEqual(self.state_mgr.state.status, PipelineStatus.SUCCESS)

    def test_cli_subcommands_init_and_status(self):
        """Test direct CLI command executions."""
        from core.spec.generator import SpecGenerator
        from core.detector import ProjectDetector

        detector_data = ProjectDetector(self.test_dir).detect()
        self.assertIn("languages", detector_data)
        gen = SpecGenerator(self.test_dir)
        files = gen.generate_defaults("Test App")
        self.assertTrue(len(files) >= 5)

        s = self.state_mgr.state
        self.assertEqual(s.status, PipelineStatus.IDLE)


if __name__ == "__main__":
    unittest.main()
