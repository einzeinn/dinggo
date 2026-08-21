import os
import re
import ast
import subprocess
import difflib
from typing import Dict, Any, List, Optional, Tuple


def read_file(path: str) -> Dict[str, Any]:
    """
    Read content of a file from disk.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"File not found: {path}", "content": ""}
    
    if os.path.isdir(abs_path):
        return {"success": False, "error": f"Path is a directory, not a file: {path}", "content": ""}

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "path": abs_path, "content": content}
    except Exception as e:
        return {"success": False, "error": f"Failed to read file: {str(e)}", "content": ""}


def write_file(path: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file. Creates parent directories if missing.
    """
    abs_path = os.path.abspath(path)
    try:
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": abs_path, "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"success": False, "error": f"Failed to write file {path}: {str(e)}"}


def list_dir(path: str = ".") -> Dict[str, Any]:
    """
    List contents of a directory.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"Directory not found: {path}", "items": []}
    
    if not os.path.isdir(abs_path):
        return {"success": False, "error": f"Path is not a directory: {path}", "items": []}

    try:
        items = []
        for item in sorted(os.listdir(abs_path)):
            item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(item_path)
            items.append({"name": item, "is_dir": is_dir, "path": item_path})
        return {"success": True, "path": abs_path, "items": items}
    except Exception as e:
        return {"success": False, "error": f"Failed to open directory {path}: {str(e)}", "items": []}


def get_unified_diff(path: str, old_content: str, new_content: str) -> str:
    """
    Generate unified diff string between old and new content.
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm=""
    )
    return "".join(diff)


def apply_search_replace_blocks(original_content: str, patch_text: str) -> Dict[str, Any]:
    """
    Parses and atomically applies SEARCH/REPLACE blocks.
    Format:
    <<<<<<< SEARCH
    old content
    =======
    new content
    >>>>>>> REPLACE

    Strict Rules:
    - 0 matches -> fail block (atomic rollback).
    - 1 match -> apply replacement.
    - >1 matches -> fail as ambiguous match.
    - Malformed tags -> fail block.
    """
    # Check for malformed tags first (e.g. SEARCH without ======= or >>>>>>> REPLACE)
    has_search = "<<<<<<< SEARCH" in patch_text
    has_sep = "=======" in patch_text
    has_replace = ">>>>>>> REPLACE" in patch_text

    if (has_search or has_sep or has_replace) and not (has_search and has_sep and has_replace):
        return {
            "success": False,
            "blocks_applied": 0,
            "error": "Malformed SEARCH/REPLACE block format: missing required <<<<<<< SEARCH, =======, or >>>>>>> REPLACE tag.",
            "content": original_content
        }

    pattern = re.compile(
        r"^\s*<<<<<<<\s*SEARCH\r?\n([\s\S]*?)\r?\n\s*=======\s*\r?\n([\s\S]*?)\r?\n\s*>>>>>>>\s*REPLACE",
        re.MULTILINE
    )

    blocks = pattern.findall(patch_text)
    if not blocks:
        return {
            "success": False,
            "blocks_applied": 0,
            "error": "No valid SEARCH/REPLACE blocks found in patch text.",
            "content": original_content
        }

    current_content = original_content
    applied_count = 0

    for search_text, replace_text in blocks:
        if not search_text:
            return {
                "success": False,
                "blocks_applied": 0,
                "error": "Malformed block: SEARCH block content cannot be empty.",
                "content": original_content
            }

        count = current_content.count(search_text)
        if count == 0:
            return {
                "success": False,
                "blocks_applied": 0,
                "error": f"Search block not found in target file: '{search_text[:60]}...'",
                "content": original_content
            }
        elif count > 1:
            return {
                "success": False,
                "blocks_applied": 0,
                "error": f"Search block matched {count} locations (ambiguous match, must match exactly 1 location): '{search_text[:60]}...'",
                "content": original_content
            }

        current_content = current_content.replace(search_text, replace_text, 1)
        applied_count += 1

    return {
        "success": True,
        "blocks_applied": applied_count,
        "content": current_content,
        "error": None
    }


def edit_file(path: str, new_content: str) -> Dict[str, Any]:
    """
    Applies modification to a file.
    Priority 1: If SEARCH/REPLACE blocks detected -> apply_search_replace_blocks.
    Priority 2: Fallback -> full replacement.
    Retains original_content for atomic failure rollback.
    """
    abs_path = os.path.abspath(path)
    old_content = ""
    if os.path.exists(abs_path):
        read_res = read_file(abs_path)
        if read_res["success"]:
            old_content = read_res["content"]

    # Priority 1: Check if new_content contains SEARCH/REPLACE blocks
    if "<<<<<<< SEARCH" in new_content:
        sr_res = apply_search_replace_blocks(old_content, new_content)
        if not sr_res["success"]:
            return {
                "success": False,
                "path": abs_path,
                "error": f"Failed to apply SEARCH/REPLACE block: {sr_res['error']}",
                "original_content": old_content
            }
        final_content = sr_res["content"]
        blocks_applied = sr_res["blocks_applied"]
    else:
        # Priority 2: Full content replacement
        final_content = new_content
        blocks_applied = 0

    diff_str = get_unified_diff(path, old_content, final_content)
    write_res = write_file(abs_path, final_content)
    if write_res["success"]:
        return {
            "success": True,
            "path": abs_path,
            "diff": diff_str,
            "bytes_written": write_res["bytes_written"],
            "blocks_applied": blocks_applied,
            "original_content": old_content,
            "code_content": final_content
        }
    return write_res


def search_code(query: str, root_dir: str = ".", max_results: int = 50) -> Dict[str, Any]:
    """
    Searches codebase for a query string or regex pattern using ripgrep with Python fallback.
    Outputs compact pointers (file:line  content).
    Ignores build/venv/.git directories.
    """
    query = query.strip()
    if not query:
        return {"success": False, "error": "Search query cannot be empty.", "output": ""}

    abs_root = os.path.abspath(root_dir)
    ignored_dirs = {".git", ".venv", "venv", "node_modules", "build", "dist", "__pycache__", ".context", "dinggo.egg-info"}

    # Attempt 1: Ripgrep execution (fastest)
    try:
        rg_cmd = [
            "rg", "--line-number", "--no-heading", "--color=never",
            "--max-count", str(max_results), "--smart-case",
            query, abs_root
        ]
        res = subprocess.run(rg_cmd, capture_output=True, text=True, timeout=5.0)
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().splitlines()[:max_results]
            formatted = []
            for l in lines:
                parts = l.split(":", 2)
                if len(parts) >= 3:
                    rel_f = os.path.relpath(parts[0], abs_root)
                    line_num = parts[1]
                    code_text = parts[2].strip()[:100]
                    formatted.append(f"{rel_f}:{line_num}  {code_text}")
                else:
                    formatted.append(l[:120])
            out_str = "\n".join(formatted)
            return {"success": True, "query": query, "matches": len(formatted), "output": out_str}
    except Exception:
        pass

    # Attempt 2: Python regex fallback
    results = []
    try:
        regex = re.compile(query, re.IGNORECASE)
    except Exception:
        regex = re.compile(re.escape(query), re.IGNORECASE)

    for root, dirs, files in os.walk(abs_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith(".")]
        for f in files:
            if len(results) >= max_results:
                break
            if f.endswith((".py", ".json", ".yaml", ".yml", ".md", ".toml", ".txt", ".html", ".css", ".js", ".ts")):
                f_path = os.path.join(root, f)
                rel_f = os.path.relpath(f_path, abs_root)
                try:
                    with open(f_path, "r", encoding="utf-8", errors="ignore") as file_obj:
                        for idx, line in enumerate(file_obj, start=1):
                            if regex.search(line):
                                code_snippet = line.strip()[:100]
                                results.append(f"{rel_f}:{idx}  {code_snippet}")
                                if len(results) >= max_results:
                                    break
                except Exception:
                    continue

    if results:
        return {"success": True, "query": query, "matches": len(results), "output": "\n".join(results)}
    return {"success": True, "query": query, "matches": 0, "output": f"No matches found for: '{query}'"}


def view_outline(path: str) -> Dict[str, Any]:
    """
    Parses Python file using AST and returns structural outline (classes, methods, functions, line ranges).
    Does NOT dump full file contents. Handles syntax_error gracefully.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"File not found: {path}", "output": ""}

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return {"success": False, "error": f"Failed to read file {path}: {str(e)}", "output": ""}

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as syn_err:
        return {
            "success": False,
            "error_type": "syntax_error",
            "file": path,
            "line": syn_err.lineno or 1,
            "column": syn_err.offset or 1,
            "message": syn_err.msg,
            "output": f"SyntaxError in {path} at line {syn_err.lineno}: {syn_err.msg}"
        }
    except Exception as ex:
        return {"success": False, "error": str(ex), "output": ""}

    rel_path = os.path.basename(path)
    outline_lines = [f"module: {rel_path}"]

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            end_line = getattr(node, "end_lineno", node.lineno)
            decs = [f"@{ast.unparse(d)}" for d in node.decorator_list] if hasattr(ast, "unparse") else []
            dec_str = f" ({', '.join(decs)})" if decs else ""
            outline_lines.append(f"\nclass {node.name}{dec_str} [{node.lineno}-{end_line}]")

            doc = ast.get_docstring(node)
            if doc:
                first_line_doc = doc.strip().splitlines()[0][:60]
                outline_lines.append(f"  doc: {first_line_doc}")

            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    f_end = getattr(item, "end_lineno", item.lineno)
                    is_async = "async " if isinstance(item, ast.AsyncFunctionDef) else ""
                    outline_lines.append(f"  {is_async}def {item.name} [{item.lineno}-{f_end}]")

        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            is_async = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            decs = [f"@{ast.unparse(d)}" for d in node.decorator_list] if hasattr(ast, "unparse") else []
            dec_str = f" ({', '.join(decs)})" if decs else ""
            outline_lines.append(f"\n{is_async}def {node.name}{dec_str} [{node.lineno}-{end_line}]")

            doc = ast.get_docstring(node)
            if doc:
                first_line_doc = doc.strip().splitlines()[0][:60]
                outline_lines.append(f"  doc: {first_line_doc}")

    output_text = "\n".join(outline_lines)
    return {"success": True, "path": path, "output": output_text}

