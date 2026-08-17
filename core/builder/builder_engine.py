"""Production Build Engine for Dinggo Product Factory."""
import os
import json
import time
from typing import Optional
from core.spec.models import ProductSpec
from core.builder.models import BuildMetadata, BuildResult, BuildArtifact
from core.builder.packager import Packager
from core.state.state_manager import StateManager, PipelinePhase, PipelineStatus


class BuildEngine:
    """Coordinates compilation, packaging, and export artifact generation."""

    def __init__(self, root_dir: str = ".", state_manager: Optional[StateManager] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.dist_dir = os.path.join(self.root_dir, "dist")
        self.state_mgr = state_manager or StateManager(self.root_dir)
        self.packager = Packager(self.root_dir)

    def build_and_export(self, spec: Optional[ProductSpec] = None) -> BuildResult:
        """Executes full production build and packaging process."""
        start_t = time.time()
        self.state_mgr.transition_to(PipelinePhase.BUILDING, PipelineStatus.IN_PROGRESS, "Packaging production artifacts into dist/", can_resume=True)

        try:
            artifacts = self.packager.package(spec=spec)

            # Metadata creation
            proj_name = spec.name if spec else self.state_mgr.state.project_name
            arch_obj = getattr(spec, "architecture", None) if spec else None
            arch_str = getattr(arch_obj, "framework", "Generic") if arch_obj else "Generic"
            meta = BuildMetadata(
                project_name=proj_name,
                version="1.0.0",
                target_architecture=arch_str or "Generic",
                entrypoint="main.py",
                artifacts=[a.path for a in artifacts]
            )

            # Save dist/metadata.json
            meta_path = os.path.join(self.dist_dir, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta.model_dump(), f, indent=2)

            artifacts.append(BuildArtifact(
                path="dist/metadata.json",
                size_bytes=os.path.getsize(meta_path),
                description="Build specification metadata"
            ))

            elapsed = round(time.time() - start_t, 2)
            self.state_mgr.transition_to(PipelinePhase.EXPORTING, PipelineStatus.IN_PROGRESS, "Build successful, awaiting Gate 3 export approval", can_resume=True)

            return BuildResult(
                success=True,
                output_dir=self.dist_dir,
                metadata=meta,
                artifacts=artifacts,
                elapsed_seconds=elapsed
            )
        except Exception as e:
            self.state_mgr.transition_to(PipelinePhase.FAILED, PipelineStatus.FAILED, f"Build failure: {str(e)}")
            return BuildResult(
                success=False,
                output_dir=self.dist_dir,
                metadata=BuildMetadata(project_name="Error"),
                artifacts=[],
                error=str(e)
            )
