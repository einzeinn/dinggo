import os
import ast
import json
import math
from typing import List, Dict, Any, Optional
from core.memory.project_context import ProjectContext


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class LongTermMemory:
    """
    Long-Term Memory Manager for Dinggo.
    Maintains Code Knowledge Graph (AST-parsed relationships) & Embeddings Vector Store
    persistently under ~/.dinggo/memory/<project>/.
    """

    def __init__(self, context: ProjectContext, ollama_client=None):
        self.context = context
        self.ollama_client = ollama_client
        self.graph_filepath = str(context.code_graph_path)
        self.vector_filepath = str(context.vector_store_path)
        
        self.code_graph: Dict[str, Any] = self._load_json(self.graph_filepath, default={"files": {}, "modules": {}})
        self.vector_store: List[Dict[str, Any]] = self._load_json(self.vector_filepath, default=[])

    def _load_json(self, path: str, default: Any) -> Any:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default

    def _save_json(self, path: str, data: Any):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def build_code_graph(self) -> Dict[str, Any]:
        """
        Scans workspace directory and builds AST knowledge graph of Python files, classes, functions, and imports.
        """
        files_graph = {}
        root_dir = self.context.working_dir

        for root, dirs, files in os.walk(root_dir):
            # Skip hidden and environment directories
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", ".venv", "__pycache__", "build", "dist")]
            
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, root_dir)
                    
                    file_info = {
                        "rel_path": rel_path,
                        "classes": [],
                        "functions": [],
                        "imports": []
                    }
                    
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            tree = ast.parse(f.read(), filename=rel_path)
                            
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                file_info["classes"].append(node.name)
                            elif isinstance(node, ast.FunctionDef):
                                file_info["functions"].append(node.name)
                            elif isinstance(node, ast.Import):
                                for alias in node.names:
                                    file_info["imports"].append(alias.name)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    file_info["imports"].append(node.module)
                    except Exception:
                        pass
                        
                    files_graph[rel_path] = file_info

        self.code_graph = {"files": files_graph}
        self._save_json(self.graph_filepath, self.code_graph)
        return self.code_graph

    def get_formatted_graph_context(self, target_scope: Optional[List[str]] = None, max_files: int = 5) -> str:
        """Returns concise string representation of Code Knowledge Graph for LLM context."""
        files = self.code_graph.get("files", {})
        if not files:
            self.build_code_graph()
            files = self.code_graph.get("files", {})

        if not files:
            return "Struktur file proyek tidak ditemukan."

        selected_files = {}
        if target_scope:
            scope_lowers = [s.lower() for s in target_scope if s]
            for path, info in files.items():
                if any(s in path.lower() for s in scope_lowers):
                    selected_files[path] = info

        if not selected_files:
            # Fallback to first max_files
            for path, info in list(files.items())[:max_files]:
                selected_files[path] = info

        lines = ["Struktur & Graph Proyek Aktif:"]
        for path, info in list(selected_files.items())[:max_files]:
            classes = ", ".join(info.get("classes", [])) or "None"
            funcs = ", ".join(info.get("functions", [])) or "None"
            imports = ", ".join(info.get("imports", [])) or "None"
            lines.append(f"  - [{path}] Class: [{classes}] | Function: [{funcs}] | Imports: [{imports}]")

        return "\n".join(lines)

    def add_vector_document(self, doc_id: str, content: str, embedding: Optional[List[float]] = None):
        """Adds a document with embedding to the vector store."""
        item = {
            "doc_id": doc_id,
            "content": content,
            "embedding": embedding or []
        }
        self.vector_store.append(item)
        self._save_json(self.vector_filepath, self.vector_store)

    def search_similar(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Searches top_k most relevant documents in vector store or keyword matches.
        """
        if not self.vector_store:
            return []

        # Simple keyword relevance scoring fallback
        query_words = set(query.lower().split())
        scored_items = []

        for item in self.vector_store:
            content = item.get("content", "").lower()
            score = sum(1.0 for w in query_words if w in content)
            scored_items.append((score, item))

        scored_items.sort(key=lambda x: x[0], reverse=True)
        return [item for score, item in scored_items[:top_k] if score > 0]
