"""Unit tests for Phase 7: Independent Reviewer Engine, Review Packages, and Investigative Loop."""
import io
import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from rich.console import Console

from core.reviewer.models import (
    ReviewReport,
    ReviewFinding,
    ReviewSeverity,
    ReviewCategory,
    ReviewPackage,
    ReviewLevel,
    ReviewMode,
    ContextRequest,
)
from core.reviewer.adapters import (
    MockReviewerAdapter,
    BaseReviewerAdapter,
    OllamaReviewerAdapter,
    CodexReviewerAdapter,
    ClaudeReviewerAdapter,
    AgyReviewerAdapter,
    OpenAICompatibleReviewerAdapter,
    ProviderRegistry,
    ProviderResolver,
    parse_review_response,
    build_audit_prompt,
    build_package_prompt,
    get_available_reviewers,
    get_reviewer_adapter,
)
from core.reviewer.package_builder import ReviewPackageBuilder
from core.reviewer.review_engine import ReviewEngine
from core.spec.models import ProductSpec, RequirementItem, ArchitectureSpec
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus
from cli.review_view import ReviewDashboard


class TestReviewerEngine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_mgr = StateManager(root_dir=self.test_dir)
        self.console = Console(file=io.StringIO(), force_terminal=False, width=120)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_mock_reviewer_clean_code(self):
        """Test auditor against clean code produces score 100 and approved verdict."""
        with open(os.path.join(self.test_dir, "clean.py"), "w") as f:
            f.write("def add(a: int, b: int) -> int:\n    return a + b\n")

        adapter = MockReviewerAdapter()
        report = adapter.audit(self.test_dir)
        self.assertEqual(report.verdict, "approved")
        self.assertEqual(report.score, 100.0)
        self.assertEqual(len(report.findings), 0)

    def test_mock_reviewer_security_findings(self):
        """Test auditor detecting hardcoded secret and eval with concrete evidence."""
        with open(os.path.join(self.test_dir, "vuln.py"), "w") as f:
            f.write(
                'API_KEY = "sk-123456789"\n'
                'def run_dynamic(cmd):\n'
                '    eval(cmd)\n'
            )

        adapter = MockReviewerAdapter()
        report = adapter.audit(self.test_dir)
        self.assertIn(report.verdict, ("revisions_required", "rejected"))
        self.assertTrue(any(f.category == ReviewCategory.SECURITY for f in report.findings))
        self.assertTrue(report.score < 80.0)
        self.assertTrue(any(f.evidence is not None for f in report.findings))

    def test_review_package_builder_targeted(self):
        """Test ReviewPackageBuilder building targeted packages for individual requirements."""
        spec = ProductSpec(
            name="TaskApp",
            requirements=[
                RequirementItem(
                    id="AUTH-001",
                    title="User Login",
                    description="Authenticate user with email and password",
                    acceptance_criteria=["Validate password", "Return JWT"]
                ),
                RequirementItem(
                    id="TASK-001",
                    title="Create Task",
                    description="Create a task for user",
                    acceptance_criteria=["Store title and description"]
                )
            ],
            architecture=ArchitectureSpec(framework="FastAPI", database="SQLite")
        )

        auth_file = os.path.join(self.test_dir, "auth_service.py")
        with open(auth_file, "w") as f:
            f.write("def login(): return {'token': 'jwt_token'}\n")

        builder = ReviewPackageBuilder(self.test_dir)
        packages = builder.build_targeted_packages(spec=spec)

        self.assertEqual(len(packages), 2)
        self.assertEqual(packages[0].requirement_id, "AUTH-001")
        self.assertEqual(packages[0].mode, ReviewMode.TARGETED)
        self.assertTrue(any("auth_service.py" in tf for tf in packages[0].target_files))
        self.assertIn("auth_service.py", packages[0].file_contents)

    def test_review_package_prompt_builder(self):
        """Test building targeted prompt from ReviewPackage."""
        pkg = ReviewPackage(
            package_id="PKG-001",
            requirement_id="AUTH-002",
            requirement_title="User Login",
            requirement_description="Authenticate email/password",
            acceptance_criteria=["Return JWT", "Reject invalid credentials"],
            target_files=["auth.py"],
            file_contents={"auth.py": "def login(): pass"},
            dependencies=["FastAPI", "PyJWT"]
        )
        prompt = build_package_prompt(pkg)
        self.assertIn("REVIEW PACKAGE", prompt)
        self.assertIn("AUTH-002", prompt)
        self.assertIn("auth.py", prompt)
        self.assertIn("PyJWT", prompt)

    def test_investigative_context_request_loop(self):
        """Test reviewer requesting missing file context and engine retrieving it."""
        spec = ProductSpec(
            name="AuthApp",
            requirements=[
                RequirementItem(
                    id="AUTH-002",
                    title="User Login",
                    description="Authenticate user credentials"
                )
            ]
        )
        # Main service file
        with open(os.path.join(self.test_dir, "auth_service.py"), "w") as f:
            f.write("from security import verify_pwd\ndef login(u, p): return verify_pwd(p)\n")
        # Imported helper file requested by reviewer
        with open(os.path.join(self.test_dir, "security.py"), "w") as f:
            f.write("def verify_pwd(p): return p == 'admin'\n")

        # Mock adapter that requests context in round 1, then approves in round 2
        class InvestigativeAdapter(BaseReviewerAdapter):
            name = "Investigative AI Auditor"
            def __init__(self):
                self.calls = 0

            def audit(self, root_dir, spec=None, package=None):
                self.calls += 1
                if self.calls == 1:
                    # Round 1: Request context
                    return ReviewReport(
                        auditor=self.name,
                        score=50.0,
                        verdict="revisions_required",
                        context_requests=[
                            ContextRequest(needed_files=["security.py"], reason="Verify password logic")
                        ]
                    )
                else:
                    # Round 2: Received context in package.additional_context
                    has_context = "security.py" in (package.additional_context if package else {})
                    return ReviewReport(
                        auditor=self.name,
                        score=95.0 if has_context else 60.0,
                        verdict="approved" if has_context else "rejected"
                    )

        adapter = InvestigativeAdapter()
        engine = ReviewEngine(self.test_dir, state_manager=self.state_mgr, adapter=adapter, mode="targeted")
        report = engine.execute_audit(spec=spec)

        self.assertEqual(adapter.calls, 2)
        self.assertEqual(report.verdict, "approved")
        self.assertEqual(report.score, 95.0)

    def test_ollama_reviewer_adapter_with_mock_client(self):
        """Test OllamaReviewerAdapter querying OllamaClient and parsing JSON review report."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.resolve_model_name.return_value = "qwen2.5-coder:7b"
        
        sample_audit_json = {
            "auditor": "Ollama Auditor (qwen2.5-coder:7b)",
            "score": 92.5,
            "verdict": "approved",
            "summary": "Codebase meets quality and security requirements.",
            "findings": [
                {
                    "id": "SEC-001",
                    "category": "security",
                    "severity": "low",
                    "requirement_id": "AUTH-001",
                    "file_path": "server.py",
                    "line_number": 15,
                    "title": "Add CSRF protection",
                    "description": "Form post does not validate CSRF token",
                    "evidence": "app.post('/login')",
                    "recommendation": "Use CSRFMiddleware"
                }
            ]
        }
        mock_client.generate.return_value = {
            "success": True,
            "response": json.dumps(sample_audit_json)
        }

        with open(os.path.join(self.test_dir, "server.py"), "w") as f:
            f.write("from fastapi import FastAPI\napp = FastAPI()\n")

        adapter = OllamaReviewerAdapter(ollama_client=mock_client, model="qwen2.5-coder:7b")
        report = adapter.audit(self.test_dir)

        self.assertEqual(report.auditor, "Ollama Auditor (qwen2.5-coder:7b)")
        self.assertEqual(report.verdict, "approved")
        self.assertEqual(len(report.findings), 1)
        self.assertEqual(report.findings[0].id, "SEC-001")
        self.assertEqual(report.findings[0].evidence, "app.post('/login')")

    def test_codex_reviewer_adapter_api_response(self):
        """Test CodexReviewerAdapter calling OpenAI-compatible API and parsing report."""
        sample_response_data = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "auditor": "Codex / OpenAI (gpt-4o)",
                            "score": 88.0,
                            "verdict": "revisions_required",
                            "summary": "One high severity security issue found.",
                            "findings": [
                                {
                                    "id": "FIND-SEC-1",
                                    "category": "security",
                                    "severity": "high",
                                    "requirement_id": "SEC-001",
                                    "file_path": "auth.py",
                                    "line_number": 42,
                                    "title": "SQL Injection vector",
                                    "description": "Raw string formatting in SQL query",
                                    "evidence": "f'SELECT * FROM users WHERE id={user_id}'",
                                    "recommendation": "Use parameterized queries"
                                }
                            ]
                        })
                    }
                }
            ]
        }

        with patch("httpx.Client") as mock_client_cls:
            mock_http_client = MagicMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = sample_response_data
            mock_http_client.post.return_value = mock_resp
            mock_client_cls.return_value.__enter__.return_value = mock_http_client

            adapter = CodexReviewerAdapter(api_key="test-sk", model="gpt-4o")
            report = adapter.audit(self.test_dir)

            self.assertEqual(report.auditor, "Codex / OpenAI (gpt-4o)")
            self.assertEqual(report.verdict, "revisions_required")
            self.assertEqual(len(report.findings), 1)
            self.assertEqual(report.findings[0].evidence, "f'SELECT * FROM users WHERE id={user_id}'")

    def test_provider_registry_and_resolver(self):
        """Test ProviderRegistry and ProviderResolver lookups."""
        self.assertIsNotNone(ProviderRegistry.get("codex"))
        self.assertIsNotNone(ProviderRegistry.get("claude"))
        self.assertIsNotNone(ProviderRegistry.get("agy"))
        self.assertIsNotNone(ProviderRegistry.get("ollama"))
        self.assertIsNotNone(ProviderRegistry.get("mock"))

        adapter = get_reviewer_adapter("mock", root_dir=self.test_dir)
        self.assertIsInstance(adapter, MockReviewerAdapter)

        available = get_available_reviewers(self.test_dir)
        self.assertTrue(any(r["id"] == "mock" for r in available))

    def test_review_engine_repair_loop(self):
        """Test review engine performing repair loop until approval."""
        vuln_file = os.path.join(self.test_dir, "app.py")
        with open(vuln_file, "w") as f:
            f.write('password = "plaintext_admin_pass"\n')

        def fix_remedy(report: ReviewReport, cycle: int):
            with open(vuln_file, "w") as f:
                f.write('import os\npassword = os.getenv("APP_PASSWORD")\n')
            return True

        mock_adapter = MockReviewerAdapter()
        engine = ReviewEngine(self.test_dir, state_manager=self.state_mgr, adapter=mock_adapter, max_cycles=3, mode="full")
        res = engine.run_review_loop(custom_fix_func=fix_remedy)

        self.assertTrue(res["success"])
        self.assertEqual(res["report"].verdict, "approved")
        self.assertEqual(self.state_mgr.state.phase, PipelinePhase.COMPLETED)
        self.assertEqual(self.state_mgr.state.status, PipelineStatus.SUCCESS)

    def test_review_dashboard_render(self):
        """Test review dashboard executes and displays results."""
        dashboard = ReviewDashboard(root_dir=self.test_dir, console=self.console, state_manager=self.state_mgr, adapter_name="mock", mode="full")
        report = dashboard.display_and_run(interactive=False)
        self.assertIsNotNone(report)
        self.assertEqual(report.verdict, "approved")


if __name__ == "__main__":
    unittest.main()
