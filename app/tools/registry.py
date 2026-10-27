"""Registro de tools: schema + handler. Toda chamada passa por auth.can_call."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from app.auth import Policies

Handler = Callable[[dict[str, Any]], Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    properties: dict[str, Any]
    required: list[str]
    handler: Handler

    def schema(self) -> FunctionSchema:
        return FunctionSchema(
            name=self.name,
            description=self.description,
            properties=self.properties,
            required=self.required,
        )


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self.tools = {t.name: t for t in tools}

    def tools_for(self, policies: Policies, caller: str) -> list[Tool]:
        allowed = policies.allowed_tools(caller)
        return [t for t in self.tools.values() if t.name in allowed]

    def schema_for(self, policies: Policies, caller: str) -> ToolsSchema:
        return ToolsSchema(standard_tools=[t.schema() for t in self.tools_for(policies, caller)])

    def register(self, llm, policies: Policies, caller: str) -> None:
        """Registra todas as tools no LLM; cada handler checa a autorização na hora da chamada."""
        for tool in self.tools.values():
            llm.register_function(tool.name, self._make_handler(tool, policies, caller))

    @staticmethod
    def _make_handler(tool: Tool, policies: Policies, caller: str):
        async def handler(params: FunctionCallParams):
            if not policies.can_call(caller, tool.name):
                await params.result_callback(
                    {"error": "not_authorized", "message": "Esta ação não é permitida para este chamador."}
                )
                return
            try:
                logger.info(f"Tool {tool.name} args={params.arguments} caller={caller}")
                await params.result_callback(await tool.handler(params.arguments))
            except Exception as e:
                logger.exception(f"Falha na tool {tool.name}")
                await params.result_callback({"error": "tool_failed", "message": str(e)})

        return handler
