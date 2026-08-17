"""Packaging & Artifact Generator for Dinggo Product Factory."""
import os
import zipfile
from typing import List, Optional
from core.spec.models import ProductSpec
from core.builder.models import BuildArtifact


class Packager:
    """Packages application into production-ready archives and container configs."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.dist_dir = os.path.join(self.root_dir, "dist")

    def package(self, spec: Optional[ProductSpec] = None) -> List[BuildArtifact]:
        """Generate all production artifacts into dist/."""
        os.makedirs(self.dist_dir, exist_ok=True)
        artifacts: List[BuildArtifact] = []

        # 1. Generate Dockerfile
        dockerfile_path = os.path.join(self.dist_dir, "Dockerfile")
        docker_content = (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY . /app\n"
            "RUN pip install --no-cache-dir -r requirements.txt || true\n"
            "EXPOSE 8000\n"
            'CMD ["python", "main.py"]\n'
        )
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(docker_content)
        artifacts.append(BuildArtifact(
            path="dist/Dockerfile",
            size_bytes=os.path.getsize(dockerfile_path),
            description="Production container definition"
        ))

        # 2. Generate docker-compose.yml
        compose_path = os.path.join(self.dist_dir, "docker-compose.yml")
        compose_content = (
            "version: '3.8'\n"
            "services:\n"
            "  app:\n"
            "    build: .\n"
            "    ports:\n"
            "      - '8000:8000'\n"
            "    environment:\n"
            "      - ENV=production\n"
        )
        with open(compose_path, "w", encoding="utf-8") as f:
            f.write(compose_content)
        artifacts.append(BuildArtifact(
            path="dist/docker-compose.yml",
            size_bytes=os.path.getsize(compose_path),
            description="Docker Compose orchestrator"
        ))

        # 3. Generate Docs
        docs_dir = os.path.join(self.dist_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        user_guide_path = os.path.join(docs_dir, "USER_GUIDE.md")
        proj_name = spec.name if spec else "Dinggo Application"
        arch_name = getattr(getattr(spec, "architecture", None), "framework", "Modern Stack") or "Modern Stack"
        guide_content = (
            f"# User Guide: {proj_name}\n\n"
            "## Getting Started\n"
            "1. Install dependencies: `pip install -r requirements.txt`\n"
            "2. Run application: `python main.py`\n\n"
            "## Architecture\n"
            f"Built with {arch_name}.\n"
        )
        with open(user_guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content)
        artifacts.append(BuildArtifact(
            path="dist/docs/USER_GUIDE.md",
            size_bytes=os.path.getsize(user_guide_path),
            description="Operational user guide"
        ))

        # 4. Generate bundle.zip
        zip_path = os.path.join(self.dist_dir, "bundle.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.root_dir):
                dirs[:] = [d for d in dirs if d not in (".git", ".venv", "dist", "__pycache__", "node_modules", ".dinggo")]
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, self.root_dir)
                    if not rel_p.startswith("dist"):
                        zipf.write(full_p, rel_p)

        artifacts.append(BuildArtifact(
            path="dist/bundle.zip",
            size_bytes=os.path.getsize(zip_path),
            description="Complete production source archive"
        ))

        return artifacts
