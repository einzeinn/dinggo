"""Pydantic data models for Product Specifications in Dinggo Product Factory."""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class RequirementItem(BaseModel):
    """Represents a single traceable functional/non-functional requirement."""
    id: str = Field(description="Unique Requirement ID, e.g. AUTH-001, INV-001")
    title: str = Field(default="", description="Short title of the requirement")
    description: str = Field(description="Detailed explanation of the requirement")
    priority: Literal["critical", "high", "medium", "low"] = "medium"
    category: str = Field(default="functional", description="functional, security, performance, ui, etc.")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Associated acceptance checks")


class ArchitectureSpec(BaseModel):
    """Architecture boundaries and constraints."""
    framework: Optional[str] = None
    runtime: Optional[str] = None
    database: Optional[str] = None
    service_boundaries: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    integration_requirements: List[str] = Field(default_factory=list)


class AcceptanceCriteria(BaseModel):
    """Acceptance criterion linked to a requirement."""
    id: str = Field(description="Criterion ID, e.g. ACC-001")
    requirement_id: Optional[str] = Field(default=None, description="Linked Requirement ID")
    description: str = Field(description="Condition that must be satisfied")
    scenario: Optional[str] = None
    expected_result: Optional[str] = None


class ProductSpec(BaseModel):
    """Master aggregated specification container."""
    name: str = Field(default="Unnamed Project", description="Product Name")
    version: str = Field(default="0.1.0", description="Product Version")
    summary: str = Field(default="", description="High-level vision & problem statement")
    target_users: List[str] = Field(default_factory=list)
    key_features: List[str] = Field(default_factory=list)
    scope: List[str] = Field(default_factory=list)
    requirements: List[RequirementItem] = Field(default_factory=list)
    architecture: ArchitectureSpec = Field(default_factory=ArchitectureSpec)
    acceptance_criteria: List[AcceptanceCriteria] = Field(default_factory=list)
    ui_spec: Dict[str, Any] = Field(default_factory=dict)
    api_spec: Dict[str, Any] = Field(default_factory=dict)
    data_model_spec: Dict[str, Any] = Field(default_factory=dict)
    raw_files: Dict[str, str] = Field(default_factory=dict, description="Raw file content map by filename")

    def get_requirement(self, req_id: str) -> Optional[RequirementItem]:
        """Look up a requirement by ID."""
        for r in self.requirements:
            if r.id.upper() == req_id.upper():
                return r
        return None


class RepairConfig(BaseModel):
    enabled: bool = True
    max_attempts: int = 5


class ApprovalConfig(BaseModel):
    plan: bool = True
    build: bool = True
    export: bool = True


class SecurityConfig(BaseModel):
    critical_failure: Literal["block", "warn", "ignore"] = "block"
    high_failure: Literal["block", "warn", "ignore"] = "block"


class ReviewConfig(BaseModel):
    required: bool = True
    default_provider: str = "codex"
    auto_revision: bool = True
    max_repair_cycles: int = 3
    mode: Literal["targeted", "full"] = "targeted"
    level: Literal["requirement", "code", "security", "full_audit"] = "requirement"


class DinggoConfig(BaseModel):
    """Root configuration schema for dinggo.yaml."""
    version: str = "1.0"
    mode: Literal["safe", "autonomous", "governed"] = "safe"
    repair: RepairConfig = Field(default_factory=RepairConfig)
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    custom_policies: Dict[str, Any] = Field(default_factory=dict)
