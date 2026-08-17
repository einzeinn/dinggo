"""Build models and schemas for Dinggo Product Factory."""
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class BuildArtifact(BaseModel):
    """Represents a generated build artifact file."""
    path: str
    size_bytes: int = 0
    description: str = ""


class BuildMetadata(BaseModel):
    """Metadata recorded with each build in dist/metadata.json."""
    project_name: str
    version: str = "1.0.0"
    build_timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    target_architecture: str = "Generic"
    entrypoint: str = "main.py"
    artifacts: List[str] = Field(default_factory=list)


class BuildResult(BaseModel):
    """Result summary of the build process."""
    success: bool
    output_dir: str
    metadata: BuildMetadata
    artifacts: List[BuildArtifact] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: Optional[str] = None
