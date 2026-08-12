import os
import difflib
from typing import Dict, Any


def read_file(path: str) -> Dict[str, Any]:
    """
    Read content of a file from disk.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"File tidak ditemukan: {path}", "content": ""}
    
    if os.path.isdir(abs_path):
        return {"success": False, "error": f"Path adalah direktori, bukan file: {path}", "content": ""}

    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"success": True, "path": abs_path, "content": content}
    except Exception as e:
        return {"success": False, "error": f"Gagal membaca file: {str(e)}", "content": ""}


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
        return {"success": False, "error": f"Gagal menulis file {path}: {str(e)}"}


def list_dir(path: str = ".") -> Dict[str, Any]:
    """
    List contents of a directory.
    """
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        return {"success": False, "error": f"Direktori tidak ditemukan: {path}", "items": []}
    
    if not os.path.isdir(abs_path):
        return {"success": False, "error": f"Path bukan direktori: {path}", "items": []}

    try:
        items = []
        for item in sorted(os.listdir(abs_path)):
            item_path = os.path.join(abs_path, item)
            is_dir = os.path.isdir(item_path)
            items.append({"name": item, "is_dir": is_dir, "path": item_path})
        return {"success": True, "path": abs_path, "items": items}
    except Exception as e:
        return {"success": False, "error": f"Gagal membuka direktori {path}: {str(e)}", "items": []}


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


def edit_file(path: str, new_content: str) -> Dict[str, Any]:
    """
    Calculate diff and apply modification to a file.
    """
    abs_path = os.path.abspath(path)
    old_content = ""
    if os.path.exists(abs_path):
        read_res = read_file(abs_path)
        if read_res["success"]:
            old_content = read_res["content"]

    diff_str = get_unified_diff(path, old_content, new_content)
    write_res = write_file(abs_path, new_content)
    if write_res["success"]:
        return {
            "success": True,
            "path": abs_path,
            "diff": diff_str,
            "bytes_written": write_res["bytes_written"]
        }
    return write_res
