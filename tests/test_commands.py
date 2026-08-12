import unittest
from unittest.mock import MagicMock
from cli.commands import SlashCommandHandler


class TestSlashCommands(unittest.TestCase):

    def setUp(self):
        self.mock_ui = MagicMock()
        self.mock_client = MagicMock()
        self.mock_context = MagicMock()
        self.mock_context.working_dir = "C:\\AI System Project\\dinggo"
        self.mock_context.get_info.return_value = {"project_name": "dinggo", "storage_dir": "test"}

        self.mock_short_mem = MagicMock()
        self.mock_short_mem.history = []
        self.mock_short_mem.get_formatted_context.return_value = "No history"

        self.mock_long_mem = MagicMock()
        self.mock_long_mem.get_formatted_graph_context.return_value = "No graph"

        self.handler = SlashCommandHandler(
            ui=self.mock_ui,
            ollama_client=self.mock_client,
            project_context=self.mock_context,
            short_term_memory=self.mock_short_mem,
            long_term_memory=self.mock_long_mem
        )

    def test_help_command(self):
        res = self.handler.handle_command("/help")
        self.assertTrue(res)
        self.mock_ui.render_help.assert_called_once()

    def test_config_command(self):
        res = self.handler.handle_command("/config")
        self.assertTrue(res)
        self.mock_ui.render_config.assert_called_once()

    def test_models_command(self):
        self.mock_client.list_installed_models.return_value = ["gemma-sea-lion", "qwen3.5:4b"]
        res = self.handler.handle_command("/models")
        self.assertTrue(res)
        self.mock_ui.render_models.assert_called_once()

    def test_status_command(self):
        res = self.handler.handle_command("/status")
        self.assertTrue(res)
        self.mock_ui.render_status.assert_called_once()

    def test_memory_command(self):
        res = self.handler.handle_command("/memory")
        self.assertTrue(res)
        self.mock_ui.render_memory_status.assert_called_once()

    def test_clear_command(self):
        res = self.handler.handle_command("/clear")
        self.assertTrue(res)
        self.mock_short_mem.clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
