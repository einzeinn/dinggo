import unittest
from unittest.mock import patch, MagicMock
from core.ollama_client import OllamaClient


class TestOllamaClient(unittest.TestCase):

    @patch("httpx.get")
    def test_is_available(self, mock_get):
        mock_get.return_value.status_code = 200
        client = OllamaClient(base_url="http://localhost:11434")
        self.assertTrue(client.is_available())

    @patch("httpx.post")
    def test_unload_model(self, mock_post):
        mock_post.return_value.status_code = 200
        client = OllamaClient(base_url="http://localhost:11434")
        client.active_model = "gemma-sea-lion"

        success = client.unload_model("gemma-sea-lion")
        self.assertTrue(success)
        self.assertIsNone(client.active_model)
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "gemma-sea-lion", "keep_alive": 0},
            timeout=5.0
        )

    @patch("httpx.post")
    def test_generate_auto_unload_previous_model(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"response": '{"status": "ok"}', "done": True}

        client = OllamaClient(base_url="http://localhost:11434")
        client.force_unload = True
        client.active_model = "model-a"

        res = client.generate("model-b", prompt="Hello")
        self.assertTrue(res["success"])
        self.assertEqual(client.active_model, "model-b")
        # Should have called post twice: 1 for unloading model-a, 1 for generate model-b
        self.assertEqual(mock_post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
