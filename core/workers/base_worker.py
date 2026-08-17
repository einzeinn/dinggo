"""Base Worker & ExecutionRecord models for Dinggo Product Factory."""
import time
from abc import ABC, abstractmethod
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

from core.planner.task_graph import TaskNode
from core.spec.models import ProductSpec


class ExecutionRecord(BaseModel):
    """Immutable record of a task execution step."""
    task_id: str
    requirement_id: Optional[str] = None
    worker_type: str
    status: Literal["completed", "failed", "skipped"]
    files_created: List[str] = Field(default_factory=list)
    files_modified: List[str] = Field(default_factory=list)
    output_summary: str = ""
    error: Optional[str] = None
    elapsed_seconds: float = 0.0
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class BaseWorker(ABC):
    """Abstract interface for domain-specific implementation workers."""

    def __init__(self, root_dir: str = ".", ollama_client: Optional[Any] = None):
        self.root_dir = root_dir
        self.client = ollama_client

    @abstractmethod
    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        """Executes the task and returns an ExecutionRecord."""
        pass
