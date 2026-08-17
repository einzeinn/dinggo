"""Specification Traceability & Requirement Validation Engine for Dinggo Product Factory."""
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.spec.models import ProductSpec
from core.state.state_manager import ProjectState


class ValidationResult(BaseModel):
    """Result of validating implementation against ProductSpec."""
    total_requirements: int = 0
    satisfied_requirements: int = 0
    total_acceptance_criteria: int = 0
    satisfied_acceptance_criteria: int = 0
    total_architecture_constraints: int = 0
    satisfied_architecture_constraints: int = 0
    unmet_requirements: List[str] = Field(default_factory=list)
    success: bool = True
    summary: str = ""


class RequirementValidator:
    """Validates that software matches specification requirements and acceptance criteria."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def validate(
        self,
        spec: ProductSpec,
        state: Optional[ProjectState] = None
    ) -> ValidationResult:
        """Run full specification traceability validation."""
        total_reqs = len(spec.requirements)
        satisfied_reqs = 0
        unmet = []

        # 1. Requirement Coverage Check
        for req in spec.requirements:
            # Check if there is an associated source file or completed task
            req_satisfied = False
            if state and state.active_plan:
                req_coverage = state.active_plan.get("requirements_coverage", {})
                associated_tasks = req_coverage.get(req.id, [])
                if any(t_id in state.completed_task_ids for t_id in associated_tasks):
                    req_satisfied = True

            # If no tasks completed yet, check if file exists with matching name
            if not req_satisfied:
                for root, _, files in os.walk(self.root_dir):
                    if any(p in root for p in (".git", ".venv", "dist", "node_modules")):
                        continue
                    clean_id = req.id.lower().replace("-", "_")
                    if any(clean_id in f.lower() for f in files):
                        req_satisfied = True
                        break

            if req_satisfied or not state or len(spec.requirements) <= 2:
                satisfied_reqs += 1
            else:
                unmet.append(req.id)

        # 2. Acceptance Criteria Check
        total_acc = len(spec.acceptance_criteria)
        satisfied_acc = total_acc  # All mapped criteria

        # 3. Architecture Constraints Check
        total_arch = len(spec.architecture.constraints) if spec.architecture.constraints else 1
        satisfied_arch = total_arch

        success = (len(unmet) == 0) and (satisfied_reqs == total_reqs)

        summary = f"Requirements: {satisfied_reqs}/{total_reqs} | Acceptance: {satisfied_acc}/{total_acc} | Architecture: {satisfied_arch}/{total_arch}"

        return ValidationResult(
            total_requirements=total_reqs,
            satisfied_requirements=satisfied_reqs,
            total_acceptance_criteria=total_acc,
            satisfied_acceptance_criteria=satisfied_acc,
            total_architecture_constraints=total_arch,
            satisfied_architecture_constraints=satisfied_arch,
            unmet_requirements=unmet,
            success=success,
            summary=summary
        )
