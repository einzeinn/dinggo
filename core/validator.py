import os
import ast
import json
import re
from typing import Dict, Any, Optional


class SemanticValidator:
    """
    Layer 4: Semantic Validator for Dinggo CLI IDE.
    Verifies that generated files match their semantic contracts:
    - Markdown (.md): Must be clean Markdown content, NOT Python code with file.write() / def generate_...
    - Python (.py): Must be syntactically valid Python (parseable by ast.parse).
    - JSON (.json): Must be valid JSON.
    - Path Normalization: Must not leak absolute Windows paths.
    """

    def validate_file(self, target_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates the file at target_path (or provided content string).
        Returns {"valid": bool, "reason": str, "suggested_action": str}
        """
        rel_path = os.path.normpath(target_path)
        ext = os.path.splitext(rel_path)[1].lower()

        # If content not passed directly, attempt to read from disk
        if content is None:
            if not os.path.exists(target_path):
                return {
                    "valid": False,
                    "reason": f"File '{target_path}' tidak ditemukan di disk.",
                    "suggested_action": "Buat ulang file."
                }
            try:
                with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                return {
                    "valid": False,
                    "reason": f"Gagal membaca file '{target_path}': {str(e)}",
                    "suggested_action": "Tulis ulang file."
                }

        # 1. Validation for Markdown files (.md, .markdown)
        if ext in (".md", ".markdown"):
            # Check for Python file.write() or def generate_ script leaks
            python_script_indicators = [
                r"def\s+generate_",
                r"with\s+open\(",
                r"file\.write\(",
                r"f\.write\("
            ]
            for pattern in python_script_indicators:
                if re.search(pattern, content):
                    return {
                        "valid": False,
                        "reason": f"File Markdown '{rel_path}' terdeteksi berisi kode script Python ({pattern}) bukannya sintaks Markdown murni.",
                        "suggested_action": "Hasilkan ulang HANYA konten Markdown murni tanpa script Python."
                    }

        # 2. Validation for Python files (.py)
        elif ext == ".py":
            try:
                ast.parse(content, filename=rel_path)
            except SyntaxError as e:
                return {
                    "valid": False,
                    "reason": f"File Python '{rel_path}' memiliki kesalahan sintaksis: baris {e.lineno}: {e.msg}",
                    "suggested_action": "Perbaiki sintaksis Python."
                }

        # 3. Validation for JSON files (.json)
        elif ext == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "reason": f"File JSON '{rel_path}' tidak valid: {str(e)}",
                    "suggested_action": "Perbaiki format JSON."
                }

        # Check for hardcoded Windows absolute path leaks like "C:\\AI\\..." in non-python files
        if ext in (".md", ".txt", ".json", ".yaml", ".yml"):
            if re.search(r"[A-Z]:\\[^\n]+", content):
                return {
                    "valid": True,  # Non-fatal warning
                    "reason": f"Peringatan: File '{rel_path}' terdeteksi mengandung path absolut Windows.",
                    "suggested_action": "Gunakan path relatif."
                }

        return {
            "valid": True,
            "reason": f"File '{rel_path}' valid secara semantik.",
            "suggested_action": None
        }

    def validate_syntax(self, path: str, content: str) -> Dict[str, Any]:
        """
        Validates exact syntax/parsing correctness for supported file types (Python, JSON, YAML).
        Returns structured dict with line and column numbers on error:
        {"valid": bool, "type": str, "file": str, "line": Optional[int], "column": Optional[int], "message": str}
        """
        rel_path = os.path.normpath(path)
        ext = os.path.splitext(rel_path)[1].lower()

        if ext == ".py":
            try:
                ast.parse(content, filename=rel_path)
                return {"valid": True, "type": "valid", "file": rel_path, "line": None, "column": None, "message": "Syntax Python valid."}
            except SyntaxError as e:
                return {
                    "valid": False,
                    "type": "syntax_error",
                    "file": rel_path,
                    "line": e.lineno or 1,
                    "column": e.offset or 1,
                    "message": f"SyntaxError di baris {e.lineno or 1}, kolom {e.offset or 1}: {e.msg}"
                }
            except Exception as ex:
                return {
                    "valid": False,
                    "type": "syntax_error",
                    "file": rel_path,
                    "line": 1,
                    "column": 1,
                    "message": str(ex)
                }

        elif ext == ".json":
            try:
                json.loads(content)
                return {"valid": True, "type": "valid", "file": rel_path, "line": None, "column": None, "message": "JSON valid."}
            except json.JSONDecodeError as e:
                return {
                    "valid": False,
                    "type": "syntax_error",
                    "file": rel_path,
                    "line": e.lineno or 1,
                    "column": e.colno or 1,
                    "message": f"JSONDecodeError di baris {e.lineno or 1}, kolom {e.colno or 1}: {e.msg}"
                }

        elif ext in (".yaml", ".yml"):
            try:
                import yaml
                yaml.safe_load(content)
                return {"valid": True, "type": "valid", "file": rel_path, "line": None, "column": None, "message": "YAML valid."}
            except Exception as e:
                line = getattr(e, "problem_mark", None)
                lineno = line.line + 1 if line else 1
                colno = line.column + 1 if line else 1
                return {
                    "valid": False,
                    "type": "syntax_error",
                    "file": rel_path,
                    "line": lineno,
                    "column": colno,
                    "message": f"YAMLError di baris {lineno}, kolom {colno}: {str(e)}"
                }

        # Unsupported file types (e.g. .md, .txt) default to valid for syntax check
        return {"valid": True, "type": "valid", "file": rel_path, "line": None, "column": None, "message": "Format file tidak memerlukan validasi sintaks khusus."}
