"""Reviewer schemas, package models, and report models for Dinggo Product Factory."""
import time
from enum import Enum
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class ReviewSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewCategory(str, Enum):
    REQUIREMENTS = "requirements"
    CODE_QUALITY = "code_quality"
    SECURITY = "security"
    ARCHITECTURE = "architecture"


class ReviewLevel(str, Enum):
    """Graduated scope levels for code review."""
    LEVEL_1_REQUIREMENT = "requirement"  # Requirement + Diff + Tests
    LEVEL_2_CODE = "code"                # Diff + Relevant Source + Tests + Dependencies
    LEVEL_3_SECURITY = "security"        # Security-sensitive diff + Auth/Config context + Tests
    LEVEL_4_FULL_AUDIT = "full_audit"    # Entire Repository + Architecture + Dependencies


class ReviewMode(str, Enum):
    """Review execution mode."""
    TARGETED = "targeted"  # Scoped Review Packages per requirement / task
    FULL = "full"          # Full repository audit


class ContextRequest(BaseModel):
    """Investigative context request emitted by reviewer when additional files are needed."""
    needed_files: List[str] = Field(default_factory=list, description="List of relative file paths requested by reviewer")
    reason: str = Field(default="", description="Reason why context is required to verify implementation")


class ReviewPackage(BaseModel):
    """
    Structured, scoped review package provided to the independent reviewer.
    Avoids repository dumping and provides targeted evidence for specific requirements.
    """
    package_id: str = "PKG-001"
    level: ReviewLevel = ReviewLevel.LEVEL_1_REQUIREMENT
    mode: ReviewMode = ReviewMode.TARGETED
    requirements: List[Any] = Field(default_factory=list, description="List of RequirementItems in this package")
    requirement_id: Optional[str] = None
    requirement_title: Optional[str] = None
    requirement_description: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    target_files: List[str] = Field(default_factory=list)
    changed_files: List[str] = Field(default_factory=list)
    file_contents: Dict[str, str] = Field(default_factory=dict)
    diffs: Dict[str, str] = Field(default_factory=dict)
    relevant_tests: List[str] = Field(default_factory=list)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    architecture_metadata: Dict[str, Any] = Field(default_factory=dict)
    previous_findings: List[Any] = Field(default_factory=list)
    additional_context: Dict[str, str] = Field(default_factory=dict, description="Additional context retrieved on demand")


class ReviewFinding(BaseModel):
    """Single finding identified during code audit with concrete evidence."""
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    requirement_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    title: str
    description: str
    evidence: Optional[str] = Field(default=None, description="Concrete snippet or function demonstrating the flaw")
    recommendation: str


class ReviewReport(BaseModel):
    """Comprehensive independent code audit report."""
    auditor: str
    score: float = 100.0
    verdict: Literal["approved", "revisions_required", "rejected"] = "approved"
    findings: List[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    mode: ReviewMode = ReviewMode.TARGETED
    packages_reviewed: int = 1
    context_requests: List[ContextRequest] = Field(default_factory=list)
    raw_response: Optional[str] = None
