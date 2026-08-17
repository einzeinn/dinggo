"""Review Package Builder for Dinggo Product Factory."""
import os
import re
from typing import List, Dict, Any, Optional

from core.reviewer.models import ReviewPackage, ReviewLevel, ReviewMode, ContextRequest
from core.spec.models import ProductSpec, RequirementItem


class ReviewPackageBuilder:
    """
    Constructs scoped Review Packages for targeted, evidence-based code audits.
    Prevents repository-wide noise and enables progressive investigation.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def build_targeted_packages(
        self,
        spec: Optional[ProductSpec] = None,
        task_graph: Optional[Any] = None,
        state: Optional[Any] = None,
        level: ReviewLevel = ReviewLevel.LEVEL_1_REQUIREMENT
    ) -> List[ReviewPackage]:
        """
        Generates targeted Review Packages scoped to individual traceable requirements.
        """
        packages: List[ReviewPackage] = []
        all_files = self._scan_repo_files()

        if spec and spec.requirements:
            for idx, req in enumerate(spec.requirements, start=1):
                # 1. Map target files from Task Graph or heuristic file resolution
                target_files = self._resolve_target_files_for_requirement(req, task_graph, all_files)
                
                # 2. Read contents of target files
                file_contents = {}
                for tf in target_files:
                    abs_path = os.path.join(self.root_dir, tf)
                    if os.path.isfile(abs_path):
                        try:
                            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                                file_contents[tf] = f.read()
                        except Exception:
                            pass

                # 3. Find relevant test files
                relevant_tests = self._find_relevant_tests(req, target_files, all_files)
                
                # 4. Extract test results from state if available
                test_results = {}
                if state and hasattr(state, "stats"):
                    total = getattr(state.stats, "tests_total", 0)
                    passed = getattr(state.stats, "tests_passed", 0)
                    test_status = "PASS" if total > 0 and passed == total else ("FAIL" if total > 0 else "NOT_EXECUTED")
                    test_results = {
                        "tests_passed": passed,
                        "tests_total": total,
                        "status": test_status
                    }
                else:
                    test_results = {"status": "NOT_EXECUTED"}

                # 5. Extract relevant dependencies
                deps = self._extract_relevant_dependencies(req, spec)

                # 6. Architecture metadata
                arch_meta = {}
                if spec and spec.architecture:
                    arch_meta = {
                        "framework": getattr(spec.architecture, "framework", None),
                        "runtime": getattr(spec.architecture, "runtime", None),
                        "database": getattr(spec.architecture, "database", None)
                    }

                pkg = ReviewPackage(
                    package_id=f"PKG-{idx:03d}",
                    level=level,
                    mode=ReviewMode.TARGETED,
                    requirement_id=req.id,
                    requirement_title=req.title,
                    requirement_description=req.description,
                    acceptance_criteria=req.acceptance_criteria,
                    target_files=target_files,
                    changed_files=target_files,
                    file_contents=file_contents,
                    relevant_tests=relevant_tests,
                    test_results=test_results,
                    dependencies=deps,
                    architecture_metadata=arch_meta,
                    previous_findings=[]
                )
                packages.append(pkg)

        # Fallback if no requirements exist: create 1 targeted package per top-level module
        if not packages:
            top_level_files = [f for f in all_files if f.endswith((".py", ".js", ".ts", ".tsx", ".yaml", ".json"))][:10]
            file_contents = {}
            for tf in top_level_files:
                abs_path = os.path.join(self.root_dir, tf)
                if os.path.isfile(abs_path):
                    try:
                        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                            file_contents[tf] = f.read()
                    except Exception:
                        pass
            packages.append(ReviewPackage(
                package_id="PKG-001",
                level=level,
                mode=ReviewMode.TARGETED,
                requirement_id="GEN-001",
                requirement_title=spec.name if spec else "Core Implementation",
                requirement_description=spec.summary if spec else "Primary module implementation",
                target_files=top_level_files,
                file_contents=file_contents
            ))

        return packages

    def build_full_package(self, spec: Optional[ProductSpec] = None) -> ReviewPackage:
        """
        Builds a Level 4 Full Audit Package covering the entire repository.
        """
        all_files = self._scan_repo_files()
        code_files = [f for f in all_files if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".yaml", ".json"))]
        
        file_contents = {}
        total_chars = 0
        for fpath in code_files:
            if total_chars > 25000:
                break
            abs_p = os.path.join(self.root_dir, fpath)
            if os.path.isfile(abs_p):
                try:
                    with open(abs_p, "r", encoding="utf-8", errors="ignore") as fp:
                        content = fp.read()
                        if len(content) > 5000:
                            content = content[:5000] + "\n... [truncated]"
                        file_contents[fpath] = content
                        total_chars += len(content)
                except Exception:
                    pass

        arch_meta = {}
        if spec and spec.architecture:
            arch_meta = {
                "framework": getattr(spec.architecture, "framework", None),
                "runtime": getattr(spec.architecture, "runtime", None),
                "database": getattr(spec.architecture, "database", None)
            }

        return ReviewPackage(
            package_id="PKG-FULL",
            level=ReviewLevel.LEVEL_4_FULL_AUDIT,
            mode=ReviewMode.FULL,
            requirement_id="FULL-AUDIT",
            requirement_title=f"{spec.name if spec else 'Repository'} Full Audit",
            requirement_description="Comprehensive repository quality, security, and architecture review",
            target_files=code_files,
            file_contents=file_contents,
            architecture_metadata=arch_meta
        )

    def retrieve_context(self, package: ReviewPackage, context_req: ContextRequest) -> ReviewPackage:
        """
        Retrieves requested files on-demand for investigative reviewer follow-up.
        """
        for req_path in context_req.needed_files:
            clean_path = req_path.strip().replace("\\", "/").lstrip("/")
            abs_path = os.path.join(self.root_dir, clean_path)
            if os.path.isfile(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as fp:
                        package.additional_context[clean_path] = fp.read()
                except Exception:
                    pass
        return package

    def _resolve_target_files_for_requirement(
        self,
        req: RequirementItem,
        task_graph: Optional[Any],
        all_files: List[str]
    ) -> List[str]:
        target_files = set()

        # 1. From Task Graph DAG if present
        if task_graph:
            tasks = getattr(task_graph, "tasks", []) if hasattr(task_graph, "tasks") else (task_graph.get("tasks", []) if isinstance(task_graph, dict) else [])
            for t in tasks:
                t_req = getattr(t, "requirement_id", None) if hasattr(t, "requirement_id") else (t.get("requirement_id") if isinstance(t, dict) else None)
                if t_req and t_req.upper() == req.id.upper():
                    t_files = getattr(t, "target_files", []) if hasattr(t, "target_files") else (t.get("target_files", []) if isinstance(t, dict) else [])
                    for tf in t_files:
                        target_files.add(tf.replace("\\", "/"))

        # 2. Heuristic resolution from requirement keyword & filenames
        if not target_files:
            keywords = [w.lower() for w in re.split(r"[-_\s]+", req.id) if len(w) > 2]
            title_words = [w.lower() for w in re.split(r"[\s,:;]+", req.title) if len(w) > 3]
            keywords.extend(title_words)

            for f in all_files:
                f_lower = f.lower()
                if any(kw in f_lower for kw in keywords) and f.endswith((".py", ".js", ".ts", ".tsx", ".yaml", ".json")):
                    target_files.add(f)

        # 3. Default fallback to top-level router/service files if still empty
        if not target_files:
            for f in all_files:
                if any(sub in f.lower() for sub in ("main.py", "app.py", "router", "service", "model")) and f.endswith((".py", ".js", ".ts")):
                    target_files.add(f)

        return sorted(list(target_files))[:6]

    def _find_relevant_tests(self, req: RequirementItem, target_files: List[str], all_files: List[str]) -> List[str]:
        tests = []
        req_kw = req.id.lower().replace("-", "_")
        for f in all_files:
            f_lower = f.lower()
            if "test" in f_lower and f.endswith((".py", ".js", ".ts")):
                if req_kw in f_lower or any(os.path.basename(tf).split(".")[0].lower() in f_lower for tf in target_files):
                    tests.append(f)
        return tests[:3]

    def _extract_relevant_dependencies(self, req: RequirementItem, spec: Optional[ProductSpec]) -> List[str]:
        deps = []
        if spec and spec.architecture and spec.architecture.framework:
            deps.append(spec.architecture.framework)
        if spec and spec.architecture and spec.architecture.database:
            deps.append(spec.architecture.database)
        if "auth" in req.id.lower() or "login" in req.title.lower():
            deps.extend(["JWT (PyJWT / jose)", "Password Hashing (bcrypt / passlib)"])
        return deps

    def _scan_repo_files(self) -> List[str]:
        ignore_dirs = {".git", ".venv", "venv", "env", "node_modules", "dist", "build", "__pycache__", ".dinggo", ".pytest_cache", ".context"}
        files_found = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith(".")]
            for file in files:
                if not file.startswith("."):
                    rel = os.path.relpath(os.path.join(root, file), self.root_dir).replace("\\", "/")
                    files_found.append(rel)
        return files_found
