"""Specification and configuration template generator for Dinggo Product Factory."""
import os
from typing import Dict, Optional


class SpecGenerator:
    """Generates standard spec/ directory templates and dinggo.yaml configuration."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.spec_dir = os.path.join(self.root_dir, "spec")
        self.config_path = os.path.join(self.root_dir, "dinggo.yaml")

    def generate_defaults(self, project_name: Optional[str] = None, force: bool = False) -> Dict[str, str]:
        """Alias for initialize_spec_directory."""
        return self.initialize_spec_directory(project_name=project_name, force=force)

    def initialize_spec_directory(self, project_name: Optional[str] = None, force: bool = False) -> Dict[str, str]:
        """Create spec/ directory with default template files."""
        os.makedirs(self.spec_dir, exist_ok=True)
        name = project_name or os.path.basename(self.root_dir)

        templates = {
            "product.md": (
                f"# {name}\n\n"
                "## Vision & Summary\n"
                f"Define the core vision and value proposition of {name}.\n\n"
                "## Target Users\n"
                "- Developers and operations engineers\n"
                "- System administrators\n\n"
                "## Key Features\n"
                "- Automated deployment pipeline\n"
                "- Real-time telemetry monitoring\n\n"
                "## Scope\n"
                "- Core API services\n"
                "- Web management dashboard\n"
            ),
            "requirements.md": (
                "# Requirements Specification\n\n"
                "```yaml\n"
                "requirements:\n"
                "  - id: AUTH-001\n"
                "    title: User Authentication\n"
                "    description: Users must be able to log in securely with JWT.\n"
                "    priority: critical\n"
                "    category: security\n"
                "    acceptance_criteria:\n"
                "      - Returns 200 and valid JWT on valid credentials\n"
                "      - Returns 401 on invalid credentials\n\n"
                "  - id: CORE-001\n"
                "    title: Health Check Endpoint\n"
                "    description: Provide a /health endpoint returning service status.\n"
                "    priority: high\n"
                "    category: functional\n"
                "    acceptance_criteria:\n"
                "      - GET /health returns HTTP 200 with status ok\n"
                "```\n"
            ),
            "architecture.md": (
                "# Architecture Specification\n\n"
                "```yaml\n"
                "framework: FastAPI + React\n"
                "runtime: Python 3.12 + Node.js 20\n"
                "database: SQLite / PostgreSQL\n"
                "service_boundaries:\n"
                "  - backend/api: REST API server\n"
                "  - frontend/web: Single Page Application\n"
                "constraints:\n"
                "  - Strict typed models with Pydantic / TypeScript\n"
                "  - Zero external plain-text secret storage\n"
                "```\n"
            ),
            "ui.md": (
                "# UI Specification\n\n"
                "## Theme\n"
                "Dark-mode first with clean minimalist cyberpunk/industrial aesthetic.\n\n"
                "## Primary Screens\n"
                "- `/login`: Authentication page\n"
                "- `/dashboard`: Main metrics overview\n"
            ),
            "api.md": (
                "# API Specification\n\n"
                "## Base URL: `/api/v1`\n\n"
                "### Endpoints\n"
                "- `POST /api/v1/auth/login`\n"
                "- `GET /api/v1/health`\n"
            ),
            "data-model.md": (
                "# Data Model Specification\n\n"
                "## Entity: User\n"
                "- `id`: UUID (Primary Key)\n"
                "- `email`: String (Unique)\n"
                "- `password_hash`: String\n"
                "- `created_at`: Timestamp\n"
            ),
            "acceptance.md": (
                "# Acceptance Criteria\n\n"
                "- **ACC-001**: All critical and high requirements have passing unit tests.\n"
                "- **ACC-002**: API response time is under 200ms on local benchmark.\n"
                "- **ACC-003**: Build passes with zero linter errors.\n"
            ),
        }

        created_files = {}
        for filename, content in templates.items():
            path = os.path.join(self.spec_dir, filename)
            if not os.path.exists(path) or force:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                created_files[filename] = path

        self.initialize_dinggo_config(force=force)
        return created_files

    def initialize_dinggo_config(self, force: bool = False) -> str:
        """Create default dinggo.yaml configuration file."""
        if not os.path.exists(self.config_path) or force:
            content = (
                "# Dinggo Product Factory Configuration\n"
                "version: \"1.0\"\n"
                "mode: safe\n\n"
                "repair:\n"
                "  enabled: true\n"
                "  max_attempts: 5\n\n"
                "approval:\n"
                "  plan: true\n"
                "  build: true\n"
                "  export: true\n\n"
                "security:\n"
                "  critical_failure: block\n"
                "  high_failure: block\n\n"
                "review:\n"
                "  required: true\n"
                "  default_provider: codex\n"
                "  auto_revision: true\n"
                "  max_repair_cycles: 3\n"
            )
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write(content)
        return self.config_path
