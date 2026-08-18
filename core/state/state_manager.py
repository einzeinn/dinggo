"""Persistent State Machine for Dinggo Product Factory."""
import os
import yaml
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class PipelinePhase(str, Enum):
    IDLE = "IDLE"
    SPEC_DISCOVERY = "SPEC_DISCOVERY"
    PLANNING = "PLANNING"
    APPROVAL_GATE_1 = "APPROVAL_GATE_1"
    IMPLEMENTING = "IMPLEMENTING"
    TESTING = "TESTING"
    REPAIRING = "REPAIRING"
    VALIDATING = "VALIDATING"
    APPROVAL_GATE_2 = "APPROVAL_GATE_2"
    BUILDING = "BUILDING"
    APPROVAL_GATE_3 = "APPROVAL_GATE_3"
    EXPORTING = "EXPORTING"
    REVIEWING = "REVIEWING"
    REVIEW_REPAIRING = "REVIEW_REPAIRING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PipelineStatus(str, Enum):
    IDLE = "IDLE"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class SessionInfo(BaseModel):
    id: str = Field(default_factory=lambda: f"DNG-SESS-{int(time.time())}")
    can_resume: bool = False
    active_task_id: Optional[str] = None
    active_step: int = 0
    repair_cycle: int = 0
    max_repair_cycles: int = 5
    review_cycle: int = 0
    max_review_cycles: int = 3
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    updated_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


class PipelineStats(BaseModel):
    requirements_total: int = 0
    requirements_passed: int = 0
    tasks_total: int = 0
    tasks_completed: int = 0
    tests_total: int = 0
    tests_passed: int = 0
    builds_count: int = 0


class ProjectState(BaseModel):
    project_name: str = "unnamed-project"
    root_path: str = "."
    phase: PipelinePhase = PipelinePhase.IDLE
    status: PipelineStatus = PipelineStatus.IDLE
    last_message: str = "Ready"
    session: SessionInfo = Field(default_factory=SessionInfo)
    stats: PipelineStats = Field(default_factory=PipelineStats)
    active_plan: Optional[Dict[str, Any]] = None
    completed_task_ids: List[str] = Field(default_factory=list)
    failed_task_ids: List[str] = Field(default_factory=list)
    task_errors: Dict[str, str] = Field(default_factory=dict)
    build_history: List[Dict[str, Any]] = Field(default_factory=list)
    review_history: List[Dict[str, Any]] = Field(default_factory=list)


class StateManager:
    """Manages reading, writing, and transitioning the persistent project state in .dinggo/state.yaml."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.dinggo_dir = os.path.join(self.root_dir, ".dinggo")
        self.state_file = os.path.join(self.dinggo_dir, "state.yaml")
        self.state: ProjectState = self._load()

    def _load(self) -> ProjectState:
        """Load state from disk or create default."""
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return ProjectState(**data)
            except Exception:
                pass
        return ProjectState(
            project_name=os.path.basename(self.root_dir),
            root_path=self.root_dir
        )

    def save(self) -> None:
        """Persist current state to .dinggo/state.yaml."""
        os.makedirs(self.dinggo_dir, exist_ok=True)
        self.state.session.updated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.state_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.state.model_dump(mode="json"), f, sort_keys=False)

    def transition_to(
        self,
        phase: PipelinePhase,
        status: PipelineStatus = PipelineStatus.IN_PROGRESS,
        message: str = "",
        can_resume: Optional[bool] = None
    ) -> None:
        """Transition pipeline state and persist."""
        self.state.phase = phase
        self.state.status = status
        if message:
            self.state.last_message = message

        if can_resume is not None:
            self.state.session.can_resume = can_resume
        elif status in (PipelineStatus.IN_PROGRESS, PipelineStatus.PAUSED, PipelineStatus.AWAITING_APPROVAL, PipelineStatus.FAILED):
            self.state.session.can_resume = True
        elif status == PipelineStatus.SUCCESS:
            self.state.session.can_resume = False

        self.save()

    def can_resume(self) -> bool:
        """Check if there is an in-progress, paused, or failed session that can be resumed."""
        return (
            self.state.session.can_resume
            and self.state.phase not in (PipelinePhase.IDLE, PipelinePhase.COMPLETED)
            and self.state.status != PipelineStatus.IDLE
        )

    def is_task_completed(self, task_id: str) -> bool:
        """Check if a task is already recorded as successfully completed."""
        return task_id in self.state.completed_task_ids

    def record_task_completed(self, task_id: str) -> None:
        """Mark a task ID as completed, remove from failed list, and update stats."""
        if task_id not in self.state.completed_task_ids:
            self.state.completed_task_ids.append(task_id)
        if task_id in self.state.failed_task_ids:
            self.state.failed_task_ids.remove(task_id)
        if task_id in self.state.task_errors:
            del self.state.task_errors[task_id]

        self.state.stats.tasks_completed = len(self.state.completed_task_ids)
        self.save()

    def record_task_failed(self, task_id: str, error: str = "") -> None:
        """Mark a task ID as failed, record its error, and preserve partial completed state."""
        if task_id not in self.state.failed_task_ids:
            self.state.failed_task_ids.append(task_id)
        if error:
            self.state.task_errors[task_id] = error
        self.save()

    def get_pending_task_ids(self, all_task_ids: List[str]) -> List[str]:
        """Returns the list of task IDs that have not yet been successfully completed."""
        completed_set = set(self.state.completed_task_ids)
        return [tid for tid in all_task_ids if tid not in completed_set]

    def get_completed_task_ids(self) -> List[str]:
        """Returns the list of completed task IDs."""
        return list(self.state.completed_task_ids)

    def record_test_result(self, total: int, passed: int) -> None:
        """Update test stats."""
        self.state.stats.tests_total = total
        self.state.stats.tests_passed = passed
        self.save()

    def reset(self) -> None:
        """Reset state back to clean IDLE state."""
        self.state = ProjectState(
            project_name=os.path.basename(self.root_dir),
            root_path=self.root_dir,
            phase=PipelinePhase.IDLE,
            status=PipelineStatus.IDLE
        )
        self.save()
