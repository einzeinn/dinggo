"""Specialized implementation workers for Dinggo Product Factory."""
import os
import time
from typing import Optional, List, Any

from core.workers.base_worker import BaseWorker, ExecutionRecord
from core.planner.task_graph import TaskNode
from core.spec.models import ProductSpec


class InfraWorker(BaseWorker):
    """Worker specialized in project scaffolding, environment configuration, and manifests."""

    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        start_t = time.time()
        files_created = []

        for target in task.target_files:
            file_path = os.path.join(self.root_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None

            if not os.path.exists(file_path):
                content = f"# {task.title}\n# Scaffolding generated for {spec.name if spec else 'Project'}\n"
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                files_created.append(target)

        elapsed = round(time.time() - start_t, 3)
        return ExecutionRecord(
            task_id=task.id,
            requirement_id=task.requirement_id,
            worker_type="infra",
            status="completed",
            files_created=files_created,
            output_summary=f"Scaffolded environment & manifests: {', '.join(task.target_files)}",
            elapsed_seconds=elapsed
        )


class DatabaseWorker(BaseWorker):
    """Worker specialized in database schemas, ORM models, and migrations."""

    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        start_t = time.time()
        files_created = []

        for target in task.target_files:
            file_path = os.path.join(self.root_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None

            content = (
                f'"""Database Schema & Models for {spec.name if spec else "Project"}"""\n'
                f"# Requirement: {task.requirement_id or 'Core Schema'}\n\n"
                "from dataclasses import dataclass\n"
                "from datetime import datetime\n"
                "from typing import Optional\n\n"
                "@dataclass\n"
                "class BaseEntity:\n"
                "    id: str\n"
                "    created_at: datetime\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            files_created.append(target)

        elapsed = round(time.time() - start_t, 3)
        return ExecutionRecord(
            task_id=task.id,
            requirement_id=task.requirement_id,
            worker_type="database",
            status="completed",
            files_created=files_created,
            output_summary=f"Initialized database models: {', '.join(task.target_files)}",
            elapsed_seconds=elapsed
        )


class BackendWorker(BaseWorker):
    """Worker specialized in REST API endpoints, business logic, and authentication."""

    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        start_t = time.time()
        files_created = []

        for target in task.target_files:
            file_path = os.path.join(self.root_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None

            content = (
                f'"""Backend Service Implementation for {task.title}"""\n'
                f"# Traceable Requirement: {task.requirement_id or 'Internal'}\n"
                f"# Description: {task.description}\n\n"
                "class ServiceHandler:\n"
                "    def process(self, payload: dict) -> dict:\n"
                "        return {'status': 'success', 'data': payload}\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            files_created.append(target)

        elapsed = round(time.time() - start_t, 3)
        return ExecutionRecord(
            task_id=task.id,
            requirement_id=task.requirement_id,
            worker_type="backend",
            status="completed",
            files_created=files_created,
            output_summary=f"Implemented backend service logic: {', '.join(task.target_files)}",
            elapsed_seconds=elapsed
        )


class FrontendWorker(BaseWorker):
    """Worker specialized in UI views, components, and layout templates."""

    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        start_t = time.time()
        files_created = []

        for target in task.target_files:
            file_path = os.path.join(self.root_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None

            content = (
                f"// UI Component: {task.title}\n"
                f"// Linked Requirement: {task.requirement_id or 'UI Layout'}\n"
                "export default function ComponentView() {\n"
                "    return <div className='container'><h1>Dinggo View</h1></div>;\n"
                "}\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            files_created.append(target)

        elapsed = round(time.time() - start_t, 3)
        return ExecutionRecord(
            task_id=task.id,
            requirement_id=task.requirement_id,
            worker_type="frontend",
            status="completed",
            files_created=files_created,
            output_summary=f"Built UI component templates: {', '.join(task.target_files)}",
            elapsed_seconds=elapsed
        )


class IntegrationWorker(BaseWorker):
    """Worker specialized in API wiring, integration hooks, and entrypoint binding."""

    def execute_task(
        self,
        task: TaskNode,
        spec: Optional[ProductSpec] = None,
        context: Optional[str] = None
    ) -> ExecutionRecord:
        start_t = time.time()
        files_created = []

        for target in task.target_files:
            file_path = os.path.join(self.root_dir, target)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) if os.path.dirname(file_path) else None

            content = (
                f'"""Integration Entrypoint for {spec.name if spec else "Application"}"""\n'
                f"# Task: {task.id} - {task.title}\n\n"
                "def start_app():\n"
                "    print('Dinggo Product Factory application online.')\n\n"
                "if __name__ == '__main__':\n"
                "    start_app()\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            files_created.append(target)

        elapsed = round(time.time() - start_t, 3)
        return ExecutionRecord(
            task_id=task.id,
            requirement_id=task.requirement_id,
            worker_type="integration",
            status="completed",
            files_created=files_created,
            output_summary=f"Integrated services & entrypoints: {', '.join(task.target_files)}",
            elapsed_seconds=elapsed
        )
