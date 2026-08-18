"""Security and Isolation Policy for Sandboxed Code Execution."""
import os
import re
from typing import Set, List, Optional
from pydantic import BaseModel, Field


DEFAULT_BLOCKED_ENV_KEYS: Set[str] = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "OLLAMA_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AZURE_OPENAI_API_KEY",
    "AZURE_CLIENT_SECRET",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GITLAB_TOKEN",
    "SLACK_TOKEN",
    "DISCORD_TOKEN",
    "DATABASE_URL",
    "DB_PASSWORD",
    "POSTGRES_PASSWORD",
    "MYSQL_PWD",
    "SECRET_KEY",
    "PRIVATE_KEY",
    "SSH_AUTH_SOCK",
}

DEFAULT_BLOCKED_ENV_PATTERNS: List[str] = [
    r".*_API_KEY$",
    r".*_SECRET.*",
    r".*_TOKEN$",
    r".*_PASSWORD$",
    r".*_AUTH_.*",
    r".*_CREDENTIALS?$",
]

DEFAULT_DANGEROUS_COMMANDS: List[str] = [
    r"rm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)+[/~]",                  # rm -rf / or rm -rf ~
    r"rmdir(\s+/[a-zA-Z]+)*\s+[c-zC-Z]:(\\|/)",             # rmdir /s /q C:\
    r"format(\s+/[a-zA-Z]+)*\s+[c-zC-Z]:",                  # format C:
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",            # fork bomb
    r"mkfs(\.[a-z0-9]+)?\s+",                               # mkfs formatting
    r"dd\s+if=.*of=/dev/[sh]d[a-z]",                        # raw block overwrite
    r"chmod\s+-R\s+777\s+[/~]",                             # dangerous global chmod
    r"del(\s+/[a-zA-Z]+)*\s+[c-zC-Z]:\\windows",            # Windows system deletion
]


class SandboxPolicy(BaseModel):
    """Configuration policy governing containment and isolation of executed scripts/commands."""
    allowed_root: str = Field(default_factory=lambda: os.path.abspath("."))
    allow_network: bool = False
    allow_outside_filesystem: bool = False
    max_timeout_seconds: float = 30.0
    max_output_bytes: int = 1_000_000
    blocked_env_keys: Set[str] = Field(default_factory=lambda: set(DEFAULT_BLOCKED_ENV_KEYS))
    blocked_env_patterns: List[str] = Field(default_factory=lambda: list(DEFAULT_BLOCKED_ENV_PATTERNS))
    dangerous_command_patterns: List[str] = Field(default_factory=lambda: list(DEFAULT_DANGEROUS_COMMANDS))

    def is_env_var_blocked(self, key: str) -> bool:
        """Determines if an environment variable name is restricted."""
        k_upper = key.upper()
        if k_upper in self.blocked_env_keys:
            return True
        for pattern in self.blocked_env_patterns:
            if re.match(pattern, k_upper, re.IGNORECASE):
                return True
        return False
