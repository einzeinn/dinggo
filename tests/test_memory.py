import os
import shutil
import tempfile
import unittest
from core.memory import ProjectContext, ShortTermMemory, LongTermMemory


class TestMemorySystem(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        # Create a sample python file in temp_dir
        self.sample_py = os.path.join(self.temp_dir, "sample.py")
        with open(self.sample_py, "w", encoding="utf-8") as f:
            f.write("import os\n\nclass SampleHelper:\n    def say_hello(self):\n        return 'hello'\n")

        self.context = ProjectContext(working_dir=self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if os.path.exists(self.context.storage_dir):
            shutil.rmtree(self.context.storage_dir, ignore_errors=True)

    def test_project_context_path_isolation(self):
        info = self.context.get_info()
        self.assertIn(".dinggo", info["storage_dir"])
        self.assertEqual(info["project_name"], os.path.basename(self.temp_dir))
        self.assertTrue(os.path.exists(info["storage_dir"]))

    def test_short_term_memory_rolling_window(self):
        short_mem = ShortTermMemory(self.context, max_turns=3)
        for i in range(1, 6):
            short_mem.add_turn(
                prompt=f"Prompt {i}",
                category="TASK",
                summary=f"Summary {i}",
                target_scope=["sample.py"]
            )

        # Should strictly enforce max_turns=3
        self.assertEqual(len(short_mem.history), 3)
        self.assertEqual(short_mem.history[0]["prompt"], "Prompt 3")
        self.assertEqual(short_mem.history[-1]["prompt"], "Prompt 5")

        ctx_str = short_mem.get_formatted_context()
        self.assertIn("Prompt 3", ctx_str)
        self.assertIn("Prompt 5", ctx_str)

    def test_long_term_code_knowledge_graph(self):
        long_mem = LongTermMemory(self.context)
        graph = long_mem.build_code_graph()

        files = graph.get("files", {})
        self.assertIn("sample.py", files)
        sample_info = files["sample.py"]
        self.assertIn("SampleHelper", sample_info["classes"])
        self.assertIn("say_hello", sample_info["functions"])
        self.assertIn("os", sample_info["imports"])

        graph_str = long_mem.get_formatted_graph_context()
        self.assertIn("sample.py", graph_str)
        self.assertIn("SampleHelper", graph_str)


if __name__ == "__main__":
    unittest.main()
