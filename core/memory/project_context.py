import os
import hashlib
from pathlib import Path


class ProjectContext:
    """
    Manages isolated project storage under ~/.dinggo/memory/<project_hash>/
    Ensures zero unwanted temporary or database files pollute the user's workspace directory.
    """

    def __init__(self, working_dir: str = None):
        self.working_dir = os.path.abspath(working_dir or os.getcwd())
        self.project_name = os.path.basename(self.working_dir) or "root"
        
        # Calculate deterministic SHA-256 hash of normalized working directory
        normalized_path = os.path.normpath(self.working_dir).lower()
        self.project_hash = hashlib.sha256(normalized_path.encode("utf-8")).hexdigest()[:12]

        # Global storage path under user's home directory
        home_dir = Path.home()
        self.storage_dir = home_dir / ".dinggo" / "memory" / f"{self.project_name}_{self.project_hash}"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.short_term_path = self.storage_dir / "short_term.json"
        self.vector_store_path = self.storage_dir / "vector_store.json"
        self.code_graph_path = self.storage_dir / "code_graph.json"

    def get_info(self) -> dict:
        return {
            "working_dir": self.working_dir,
            "project_name": self.project_name,
            "project_hash": self.project_hash,
            "storage_dir": str(self.storage_dir)
        }
