import json
import os
from typing import List, Dict, Any, Optional
from core.memory.project_context import ProjectContext


class ShortTermMemory:
    """
    Short-Term Memory Manager for Dinggo.
    Maintains a rolling window of recent turns (prompts, intents, responses, and execution results)
    persistently in ~/.dinggo/memory/<project>/short_term.json.
    """

    def __init__(self, context: ProjectContext, max_turns: int = 10):
        self.context = context
        self.max_turns = max_turns
        self.filepath = str(context.short_term_path)
        self.history: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def add_turn(
        self,
        prompt: str,
        category: str,
        summary: str,
        target_scope: List[str] = None,
        direct_response: Optional[str] = None,
        execution_summary: Optional[str] = None
    ):
        turn_data = {
            "prompt": prompt,
            "category": category,
            "summary": summary,
            "target_scope": target_scope or [],
            "direct_response": direct_response,
            "execution_summary": execution_summary
        }
        self.history.append(turn_data)

        # Enforce rolling window limit
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns:]

        self.save()

    def get_formatted_context(self) -> str:
        """Formats recent history for LLM prompt context injection."""
        if not self.history:
            return "No previous conversation history."

        formatted_lines = []
        for idx, turn in enumerate(self.history, 1):
            prompt = turn.get("prompt", "")
            cat = turn.get("category", "TASK")
            summary = turn.get("summary", "")
            scope = ", ".join(turn.get("target_scope", [])) or "N/A"
            resp = turn.get("direct_response")
            exec_sum = turn.get("execution_summary")

            line = f"Turn {idx}:\n  - User Prompt: \"{prompt}\"\n  - Category: {cat}\n  - Intent: {summary}\n  - Scope: {scope}"
            if resp:
                line += f"\n  - Response: \"{resp}\""
            if exec_sum:
                line += f"\n  - Execution Result: {exec_sum}"

            formatted_lines.append(line)

        return "\n".join(formatted_lines)

    def clear(self):
        """Clears short-term history."""
        self.history = []
        self.save()
