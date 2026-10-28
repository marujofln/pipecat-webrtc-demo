"""Tool registry: schema + handler. Every call goes through auth.can_call."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from loguru import logger
from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.adapters.llm.schemas.tools_schema import ToolsSchema
from pipecat.services.llm_service import FunctionCallParams

from app.auth import Policies
from app.logutil import mask

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
        """Registers every tool on the LLM; each handler checks authorization at call time."""
        for tool in self.tools.values():
            llm.register_function(tool.name, self._make_handler(tool, policies, caller))

    @staticmethod
    def _make_handler(tool: Tool, policies: Policies, caller: str):
        async def handler(params: FunctionCallParams):
            if not policies.can_call(caller, tool.name):
                await params.result_callback(
                    {"error": "not_authorized", "message": "This action is not allowed for this caller."}
                )
                return
            try:
                # Argument values can be personal data (names), so only their keys are logged.
                logger.info(f"Tool {tool.name} args={sorted(params.arguments)} caller={mask(caller)}")
                await params.result_callback(await tool.handler(params.arguments))
            except Exception as e:
                logger.exception(f"Tool {tool.name} failed")
                # Internal details (URLs, stack data) stay in the log; the LLM gets a generic error.
                message = str(e) if isinstance(e, ValueError) else "The service is unavailable right now."
                await params.result_callback({"error": "tool_failed", "message": message})

        return handler
