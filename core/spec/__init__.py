"""Specification models and parser package for Dinggo Product Factory."""
from core.spec.models import (
    RequirementItem,
    ProductSpec,
    ArchitectureSpec,
    AcceptanceCriteria,
    DinggoConfig,
)
from core.spec.parser import SpecParser
from core.spec.generator import SpecGenerator

__all__ = [
    "RequirementItem",
    "ProductSpec",
    "ArchitectureSpec",
    "AcceptanceCriteria",
    "DinggoConfig",
    "SpecParser",
    "SpecGenerator",
]
