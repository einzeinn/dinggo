"""
Tools layer for Dinggo CLI IDE.
Provides file operations and shell execution wrappers.
"""

from tools.file_ops import (
    read_file, write_file, list_dir, edit_file, get_unified_diff,
    apply_search_replace_blocks, search_code, view_outline
)
from tools.shell_ops import run_command

__all__ = [
    "read_file",
    "write_file",
    "list_dir",
    "edit_file",
    "get_unified_diff",
    "apply_search_replace_blocks",
    "search_code",
    "view_outline",
    "run_command",
]
