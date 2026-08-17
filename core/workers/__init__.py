"""Workers package for Dinggo Product Factory."""
from typing import Dict, Type
from core.workers.base_worker import BaseWorker, ExecutionRecord
from core.workers.specialized_workers import (
    InfraWorker,
    DatabaseWorker,
    BackendWorker,
    FrontendWorker,
    IntegrationWorker,
)

WORKER_REGISTRY: Dict[str, Type[BaseWorker]] = {
    "infra": InfraWorker,
    "database": DatabaseWorker,
    "backend": BackendWorker,
    "frontend": FrontendWorker,
    "integration": IntegrationWorker,
    "general": BackendWorker,
}


def get_worker_for_type(worker_type: str, root_dir: str = ".", ollama_client=None) -> BaseWorker:
    """Instantiate the appropriate worker class based on worker_type."""
    worker_cls = WORKER_REGISTRY.get(worker_type.lower(), BackendWorker)
    return worker_cls(root_dir=root_dir, ollama_client=ollama_client)


__all__ = [
    "BaseWorker",
    "ExecutionRecord",
    "InfraWorker",
    "DatabaseWorker",
    "BackendWorker",
    "FrontendWorker",
    "IntegrationWorker",
    "WORKER_REGISTRY",
    "get_worker_for_type",
]
