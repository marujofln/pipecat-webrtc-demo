"""Autorização de tools por chamador. A barreira real fica aqui, não no prompt."""

from pathlib import Path

import yaml
from loguru import logger

POLICIES_PATH = Path(__file__).resolve().parent.parent / "agent" / "policies.yaml"


class Policies:
    def __init__(self, data: dict):
        self.roles = {name: set(r.get("tools", [])) for name, r in data.get("roles", {}).items()}
        self.callers = {str(k): v for k, v in data.get("callers", {}).items()}
        self.default_role = data.get("default_role", "guest")

    @classmethod
    def load(cls, path: Path = POLICIES_PATH) -> "Policies":
        return cls(yaml.safe_load(path.read_text()))

    def role_of(self, caller: str) -> str:
        return self.callers.get(caller.lstrip("+"), self.default_role)

    def allowed_tools(self, caller: str) -> set[str]:
        return self.roles.get(self.role_of(caller), set())

    def can_call(self, caller: str, tool: str) -> bool:
        allowed = tool in self.allowed_tools(caller)
        if not allowed:
            logger.warning(f"Tool negada: {tool} para {caller} (papel {self.role_of(caller)})")
        return allowed
