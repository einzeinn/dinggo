"""Unit tests for Phase 2: Interactive Interface, Wizard, and Settings."""
import io
import os
import shutil
import tempfile
import unittest
from rich.console import Console

from cli.wizard import ProductFactoryWizard
from cli.settings_view import SettingsView
from cli.interface import ProductFactoryInterface
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class TestInteractiveWizardAndSettings(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_wizard_non_interactive_flow(self):
        """Test wizard non-interactive execution from project detection to plan approval."""
        wizard = ProductFactoryWizard(
            root_dir=self.test_dir,
            console=self.console,
            state_manager=self.state_mgr,
            non_interactive=True
        )

        success = wizard.run()
        self.assertTrue(success)

        # Verify spec was generated
        self.assertTrue(os.path.isdir(os.path.join(self.test_dir, "spec")))
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir, "spec", "requirements.md")))

        # Verify state transitioned to IMPLEMENTING
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.IMPLEMENTING)
        self.assertEqual(self.state_mgr.state.status, PipelineStatus.IN_PROGRESS)
        self.assertTrue(self.state_mgr.can_resume())
        self.assertTrue(self.state_mgr.state.stats.requirements_total >= 2)

    def test_settings_view_persistence(self):
        """Test loading, modifying, and saving dinggo.yaml configuration."""
        settings = SettingsView(root_dir=self.test_dir, console=self.console)
        self.assertEqual(settings.config.mode, "safe")

        # Modify values
        settings.config.mode = "autonomous"
        settings.config.repair.max_attempts = 8
        settings.config.review.default_provider = "claude"
        settings.save_config()

        # Reload from disk
        reloaded = SettingsView(root_dir=self.test_dir, console=self.console)
        self.assertEqual(reloaded.config.mode, "autonomous")
        self.assertEqual(reloaded.config.repair.max_attempts, 8)
        self.assertEqual(reloaded.config.review.default_provider, "claude")

    def test_interface_session_detection(self):
        """Test interactive interface instantiation and resumable session recognition."""
        self.state_mgr.transition_to(PipelinePhase.TESTING, PipelineStatus.IN_PROGRESS, "Running tests", can_resume=True)
        interface = ProductFactoryInterface(root_dir=self.test_dir, console=self.console)
        self.assertTrue(interface.state_mgr.can_resume())


if __name__ == "__main__":
    unittest.main()
