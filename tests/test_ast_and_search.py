import os
import tempfile
import unittest
from tools.file_ops import (
    apply_search_replace_blocks, edit_file, search_code, view_outline, read_file
)
from core.validator import SemanticValidator


class TestASTAndSearch(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.validator = SemanticValidator()

    def test_apply_search_replace_blocks_single(self):
        original = "def hello():\n    print('old')\n"
        patch = (
            "<<<<<<< SEARCH\n"
            "    print('old')\n"
            "=======\n"
            "    print('new')\n"
            ">>>>>>> REPLACE"
        )
        res = apply_search_replace_blocks(original, patch)
        self.assertTrue(res["success"])
        self.assertEqual(res["blocks_applied"], 1)
        self.assertIn("print('new')", res["content"])

    def test_apply_search_replace_blocks_multiple(self):
        original = "a = 1\nb = 2\nc = 3\n"
        patch = (
            "<<<<<<< SEARCH\n"
            "a = 1\n"
            "=======\n"
            "a = 100\n"
            ">>>>>>> REPLACE\n\n"
            "<<<<<<< SEARCH\n"
            "c = 3\n"
            "=======\n"
            "c = 300\n"
            ">>>>>>> REPLACE"
        )
        res = apply_search_replace_blocks(original, patch)
        self.assertTrue(res["success"])
        self.assertEqual(res["blocks_applied"], 2)
        self.assertIn("a = 100", res["content"])
        self.assertIn("c = 300", res["content"])

    def test_apply_search_replace_blocks_zero_match(self):
        original = "def foo(): pass\n"
        patch = (
            "<<<<<<< SEARCH\n"
            "def bar(): pass\n"
            "=======\n"
            "def bar(): return True\n"
            ">>>>>>> REPLACE"
        )
        res = apply_search_replace_blocks(original, patch)
        self.assertFalse(res["success"])
        self.assertEqual(res["blocks_applied"], 0)
        self.assertEqual(res["content"], original)

    def test_apply_search_replace_blocks_ambiguous_multiple_match(self):
        original = "val = 1\nval = 1\n"
        patch = (
            "<<<<<<< SEARCH\n"
            "val = 1\n"
            "=======\n"
            "val = 2\n"
            ">>>>>>> REPLACE"
        )
        res = apply_search_replace_blocks(original, patch)
        self.assertFalse(res["success"])
        self.assertIn("ambiguous match", res["error"].lower())
        self.assertEqual(res["content"], original)

    def test_apply_search_replace_blocks_malformed(self):
        original = "x = 10\n"
        patch = "<<<<<<< SEARCH\nx = 10\n=======\nx = 20"
        res = apply_search_replace_blocks(original, patch)
        self.assertFalse(res["success"])
        self.assertIn("Malformed", res["error"])
        self.assertEqual(res["content"], original)

    def test_edit_file_atomic_failure_preserves_file(self):
        file_path = os.path.join(self.temp_dir, "atomic_test.py")
        original_code = "def init(): return True\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original_code)

        bad_patch = (
            "<<<<<<< SEARCH\n"
            "non_existent_function()\n"
            "=======\n"
            "new_code()\n"
            ">>>>>>> REPLACE"
        )
        res = edit_file(file_path, bad_patch)
        self.assertFalse(res["success"])

        # Verify original file content is untouched
        with open(file_path, "r", encoding="utf-8") as f:
            current_on_disk = f.read()
        self.assertEqual(current_on_disk, original_code)

    def test_search_code_matches_and_ignores(self):
        f1 = os.path.join(self.temp_dir, "auth.py")
        with open(f1, "w", encoding="utf-8") as f:
            f.write("class Authentication:\n    def authenticate(): pass\n")

        # Create ignored folder
        ignored_folder = os.path.join(self.temp_dir, ".venv")
        os.makedirs(ignored_folder, exist_ok=True)
        f2 = os.path.join(ignored_folder, "auth_ignored.py")
        with open(f2, "w", encoding="utf-8") as f:
            f.write("class Authentication: pass\n")

        res = search_code("Authentication", root_dir=self.temp_dir)
        self.assertTrue(res["success"])
        self.assertEqual(res["matches"], 1)
        self.assertIn("auth.py", res["output"])
        self.assertNotIn("auth_ignored.py", res["output"])

    def test_view_outline_python_structures(self):
        py_file = os.path.join(self.temp_dir, "app.py")
        code = (
            "import os\n\n"
            "@decorator\n"
            "class Server:\n"
            "    '''Server class doc.'''\n"
            "    def __init__(self): pass\n"
            "    async def start(self): pass\n\n"
            "def create_app():\n"
            "    pass\n"
        )
        with open(py_file, "w", encoding="utf-8") as f:
            f.write(code)

        res = view_outline(py_file)
        self.assertTrue(res["success"])
        out = res["output"]
        self.assertIn("class Server", out)
        self.assertIn("def __init__", out)
        self.assertIn("async def start", out)
        self.assertIn("def create_app", out)

    def test_view_outline_invalid_python_syntax(self):
        bad_py = os.path.join(self.temp_dir, "bad.py")
        with open(bad_py, "w", encoding="utf-8") as f:
            f.write("def broken_function(:\n    pass")

        res = view_outline(bad_py)
        self.assertFalse(res["success"])
        self.assertEqual(res["error_type"], "syntax_error")
        self.assertIn("SyntaxError", res["output"])

    def test_validate_syntax_python_json_yaml(self):
        # Valid Python
        py_val = self.validator.validate_syntax("test.py", "x = 1 + 2\n")
        self.assertTrue(py_val["valid"])

        # Invalid Python
        py_inval = self.validator.validate_syntax("test.py", "def foo(:\n")
        self.assertFalse(py_inval["valid"])
        self.assertEqual(py_inval["type"], "syntax_error")

        # Valid JSON
        json_val = self.validator.validate_syntax("test.json", '{"key": "value"}')
        self.assertTrue(json_val["valid"])

        # Invalid JSON
        json_inval = self.validator.validate_syntax("test.json", '{"key": value}')
        self.assertFalse(json_inval["valid"])

        # Valid YAML
        yaml_val = self.validator.validate_syntax("test.yaml", "key: value\nlist:\n  - item\n")
        self.assertTrue(yaml_val["valid"])


if __name__ == "__main__":
    unittest.main()
