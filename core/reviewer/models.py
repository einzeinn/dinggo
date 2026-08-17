"""Reviewer schemas and report models for Dinggo Product Factory."""
import time
from enum import Enum
from typing import List, Optional, Literal
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


class ReviewFinding(BaseModel):
    """Single finding identified during code audit."""
    id: str
    category: ReviewCategory
    severity: ReviewSeverity
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    title: str
    description: str
    recommendation: str


class ReviewReport(BaseModel):
    """Comprehensive independent code audit report."""
    auditor: str
    score: float = 100.0
    verdict: Literal["approved", "revisions_required", "rejected"] = "approved"
    findings: List[ReviewFinding] = Field(default_factory=list)
    summary: str = ""
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
