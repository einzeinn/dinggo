import os
import tempfile
import shutil
import unittest
from core.validator import SemanticValidator
from core.codegen import extract_content_block, CodegenDelegate


class TestSemanticValidator(unittest.TestCase):

    def setUp(self):
        self.validator = SemanticValidator()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_markdown_validation_python_leak(self):
        # Case A: Markdown containing Python file.write script (INVALID)
        python_leak = (
            "def generate_readme():\n"
            "    with open('docs/README.md', 'w') as f:\n"
            "        f.write('# Hello World')\n"
            "generate_readme()"
        )
        res_a = self.validator.validate_file("docs/README.md", content=python_leak)
        self.assertFalse(res_a["valid"])
        self.assertIn("terdeteksi berisi kode script Python", res_a["reason"])

        # Case B: Clean Markdown (VALID)
        clean_md = (
            "# Dinggo Project Readiness\n\n"
            "## Overview\n"
            "Dinggo is a local CLI IDE orchestrator."
        )
        res_b = self.validator.validate_file("docs/README.md", content=clean_md)
        self.assertTrue(res_b["valid"])

    def test_python_syntax_validation(self):
        # Case A: Valid Python
        valid_py = "def add(a, b):\n    return a + b\n"
        res_a = self.validator.validate_file("utils.py", content=valid_py)
        self.assertTrue(res_a["valid"])

        # Case B: Syntax Error
        invalid_py = "def add(a, b\n    return a + b"
        res_b = self.validator.validate_file("utils.py", content=invalid_py)
        self.assertFalse(res_b["valid"])

    def test_json_validation(self):
        # Case A: Valid JSON
        valid_json = '{"name": "dinggo", "version": "0.1.0"}'
        res_a = self.validator.validate_file("config.json", content=valid_json)
        self.assertTrue(res_a["valid"])

        # Case B: Invalid JSON
        invalid_json = '{"name": "dinggo", version: 0.1.0}'
        res_b = self.validator.validate_file("config.json", content=invalid_json)
        self.assertFalse(res_b["valid"])

    def test_extract_content_block(self):
        # Test stripping python file.write wrapper for markdown files
        raw_llm_out = (
            "```python\n"
            "with open('docs/README.md', 'w') as file:\n"
            "    file.write('# System Ready\\n')\n"
            "    file.write('All systems operational.\\n')\n"
            "```"
        )
        cleaned = extract_content_block(raw_llm_out, ext=".md")
        self.assertNotIn("with open", cleaned)
        self.assertIn("# System Ready", cleaned)


if __name__ == "__main__":
    unittest.main()
