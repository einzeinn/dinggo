"""
Core orchestration layer for Dinggo CLI IDE.
Contains Ollama REST client and Layer 1 (Intent), Layer 2 (Planner), Layer 3 (Executor/Codegen).
"""

from core.ollama_client import OllamaClient
from core.intent_parser import IntentParser, IntentSchema
from core.planner import Planner, PlanSchema, PlanStep
from core.codegen import CodegenDelegate
from core.executor import Executor

__all__ = [
    "OllamaClient",
    "IntentParser",
    "IntentSchema",
    "Planner",
    "PlanSchema",
    "PlanStep",
    "CodegenDelegate",
    "Executor",
]
