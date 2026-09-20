"""Provider-agnostic message/response types for agent-core.

These are what LLMProvider implementations speak — the agent loop only
ever deals in these types, never in a specific provider's SDK types.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCallRequest(BaseModel):
    """A tool call the LLM wants to make, as parsed out of its response."""

    id: str = Field(description="Provider-assigned call id, echoed back in the tool result message.")
    name: str = Field(description="Tool name, matching a ToolContract.name in the Tool Gateway.")
    arguments: dict[str, Any] = Field(description="Parsed arguments for the tool call.")


class Message(BaseModel):
    """One turn in the conversation, in the shape every provider adapter must accept/emit."""

    role: Role
    content: str | None = None

    # Present when role == ASSISTANT and the model asked to call tools.
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)

    # Present when role == TOOL: which call this message is the result of.
    tool_call_id: str | None = None
    name: str | None = None


class ToolSpec(BaseModel):
    """Tool description passed to the LLM so it can decide whether/how to call it.

    Built from a Tool Gateway ToolContract, not from the contract itself, so
    agent-core doesn't need to import tool_gateway's pydantic models directly
    into the wire format sent to providers.
    """

    name: str
    description: str
    parameters: dict[str, Any] = Field(description="JSON Schema for the tool's input.")


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    """What every LLMProvider.complete() call returns, regardless of provider."""

    content: str | None = None
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    stop_reason: Literal["end_turn", "tool_use", "max_tokens", "error"] = "end_turn"
    usage: Usage = Field(default_factory=Usage)
    raw: dict[str, Any] = Field(default_factory=dict, description="Original provider response, for debugging.")
