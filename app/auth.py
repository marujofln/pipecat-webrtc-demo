"""Per-caller tool authorization and language mapping. This is the real gate, not the prompt."""

from pathlib import Path

import yaml
from loguru import logger

POLICIES_PATH = Path(__file__).resolve().parent.parent / "agent" / "policies.yaml"


class Policies:
    def __init__(self, data: dict):
        self.roles = {name: set(r.get("tools", [])) for name, r in data.get("roles", {}).items()}
        self.default_role = data.get("default_role", "guest")
        self.language_prefixes = {
            str(k): v for k, v in (data.get("languages") or {}).get("by_prefix", {}).items()
        }
        self.callers: dict[str, str] = {}
        self.caller_languages: dict[str, str] = {}
        for caller, entry in data.get("callers", {}).items():
            if isinstance(entry, dict):
                self.callers[str(caller)] = entry.get("role", self.default_role)
                if entry.get("language"):
                    self.caller_languages[str(caller)] = entry["language"]
            else:
                self.callers[str(caller)] = entry

    @classmethod
    def load(cls, path: Path = POLICIES_PATH) -> "Policies":
        return cls(yaml.safe_load(path.read_text()))

    def role_of(self, caller: str) -> str:
        return self.callers.get(caller.lstrip("+"), self.default_role)

    def language_of(self, caller: str) -> str | None:
        """Caller's explicit language, else the longest matching country code, else None."""
        caller = caller.lstrip("+")
        if caller in self.caller_languages:
            return self.caller_languages[caller]
        matches = [p for p in self.language_prefixes if caller.isdigit() and caller.startswith(p)]
        return self.language_prefixes[max(matches, key=len)] if matches else None

    def allowed_tools(self, caller: str) -> set[str]:
        return self.roles.get(self.role_of(caller), set())

    def can_call(self, caller: str, tool: str) -> bool:
        allowed = tool in self.allowed_tools(caller)
        if not allowed:
            logger.warning(f"Tool denied: {tool} for {caller} (role {self.role_of(caller)})")
        return allowed
