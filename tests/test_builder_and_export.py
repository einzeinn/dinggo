"""Unit tests for Phase 6: Production Build, Packaging & Export Gate 3."""
import io
import os
import shutil
import tempfile
import unittest
from rich.console import Console

from core.builder.packager import Packager
from core.builder.builder_engine import BuildEngine
from core.spec.models import ProductSpec, ArchitectureSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from cli.gates.export_review import ExportReviewGate


class TestBuilderAndExport(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

        # Create dummy file to pack
        with open(os.path.join(self.test_dir, "main.py"), "w") as f:
            f.write("print('Hello Dinggo')\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_packager(self):
        """Test Packager generates docker, docs, and bundle.zip."""
        packager = Packager(root_dir=self.test_dir)
        spec = ProductSpec(name="Demo Product", architecture=ArchitectureSpec(framework="FastAPI"))
        artifacts = packager.package(spec)

        self.assertTrue(len(artifacts) >= 4)
        dist_dir = os.path.join(self.test_dir, "dist")
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "Dockerfile")))
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "docker-compose.yml")))
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "docs", "USER_GUIDE.md")))
        self.assertTrue(os.path.isfile(os.path.join(dist_dir, "bundle.zip")))

    def test_build_engine(self):
        """Test BuildEngine orchestrating build and metadata generation."""
        engine = BuildEngine(root_dir=self.test_dir, state_manager=self.state_mgr)
        spec = ProductSpec(name="Demo Product")
        res = engine.build_and_export(spec)

        self.assertTrue(res.success)
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.EXPORTING)
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "dist", "metadata.json")))

    def test_export_review_gate(self):
        """Test ExportReviewGate non-interactive approval and state finalization."""
        engine = BuildEngine(root_dir=self.test_dir, state_manager=self.state_mgr)
        res = engine.build_and_export()

        gate = ExportReviewGate(console=self.console, state_manager=self.state_mgr)
        approved, feedback = gate.review_and_confirm(res, non_interactive=True)

        self.assertTrue(approved)
        self.assertIsNone(feedback)
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.COMPLETED)
        self.assertEqual(self.state_mgr.state.status, PipelineStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()
