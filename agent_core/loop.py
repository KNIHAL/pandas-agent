"""Core agent loop: plan -> select tool -> execute -> observe -> repeat.

AgentLoop is provider-agnostic (any LLMProvider) and tool-executor-agnostic
(anything shaped like ToolExecutor below) — it does not import tool_gateway.
Hooking a real ToolGateway in is the next task; ToolGateway.invoke already
matches the ToolExecutor.invoke signature structurally, so that hook-up is
expected to be thin glue code, not a new abstraction.
"""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from .context import ConversationContext
from .llm_provider import LLMProvider
from .messages import Message, Role, ToolCallRequest, ToolSpec


class AgentLoopError(Exception):
    """Raised when the loop can't reach a final answer (e.g. max_iterations)."""


@runtime_checkable
class ToolExecutor(Protocol):
    """Anything that can execute a tool call by name.

    tool_gateway.ToolGateway.invoke(tool_name, raw_input) matches this
    signature, and its ToolResult (success/data/error) matches the
    structural shape AgentLoop expects back — no adapter needed.
    """

    def invoke(self, tool_name: str, raw_input: dict[str, Any]) -> Any: ...


class AgentLoop:
    def __init__(
        self,
        provider: LLMProvider,
        tool_executor: ToolExecutor,
        tools: list[ToolSpec] | None = None,
        max_iterations: int = 10,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> None:
        self._provider = provider
        self._tool_executor = tool_executor
        self._tools = tools
        self._max_iterations = max_iterations
        self._max_tokens = max_tokens
        self._temperature = temperature

    def run(self, context: ConversationContext, *, max_iterations: int | None = None) -> Message:
        """Run the loop until the LLM gives a final answer (no tool_calls).

        Appends every assistant/tool message it produces to `context` as it
        goes, then returns the final assistant Message.
        """
        limit = max_iterations if max_iterations is not None else self._max_iterations

        for _ in range(limit):
            response = self._provider.complete(
                context.history(),
                tools=self._tools,
                system=context.system,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )

            assistant_msg = context.add_assistant(content=response.content, tool_calls=response.tool_calls)

            if not response.tool_calls:
                return assistant_msg

            for tool_call in response.tool_calls:
                result = self._tool_executor.invoke(tool_call.name, tool_call.arguments)
                context.add_tool_result(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=self._result_to_content(result),
                )

        raise AgentLoopError(f"Exceeded max_iterations ({limit}) without a final answer.")

    @staticmethod
    def _result_to_content(result: Any) -> str:
        """Turn a ToolExecutor result into the string a TOOL message carries.

        Duck-typed against tool_gateway.ToolResult's shape (success/data/error)
        without importing it, per the module boundary described above.
        """
        success = getattr(result, "success", None)

        if success is False:
            error = getattr(result, "error", None)
            message = getattr(error, "message", None) or str(error) if error is not None else "Unknown error"
            return f"ERROR: {message}"

        data = getattr(result, "data", result)
        return AgentLoop._stringify(data)

    @staticmethod
    def _stringify(data: Any) -> str:
        if data is None:
            return ""
        if isinstance(data, str):
            return data
        if isinstance(data, BaseModel):
            return data.model_dump_json()
        if isinstance(data, (dict, list)):
            return json.dumps(data)
        return str(data)
