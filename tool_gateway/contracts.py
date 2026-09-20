"""Tool contract schema for the tool-gateway module.

Every tool exposed to agent-core must be registered with a ToolContract.
The gateway uses this contract to validate input, enforce permissions and
limits, apply timeouts, and decide failure behavior before/after invoking
the underlying tool implementation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Type

from pydantic import BaseModel, Field


class Permission(str, Enum):
    """Access level a tool requires."""

    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    EXECUTE_CODE = "execute_code"
    NETWORK = "network"
    ARTIFACT_WRITE = "artifact_write"


class FailureBehavior(str, Enum):
    """How the gateway should handle a tool failure."""

    RAISE = "raise"                  # propagate exception to agent-core
    RETURN_ERROR = "return_error"    # return a structured error result
    RETRY_ONCE = "retry_once"        # retry once, then RETURN_ERROR


class ToolLimits(BaseModel):
    """Resource limits enforced by the gateway for a single tool call."""

    max_rows: int | None = Field(
        default=None, description="Max rows a tool may return/process. None = no row limit."
    )
    max_query_seconds: float | None = Field(
        default=None,
        description=(
            "Max wall-clock seconds for the underlying query/op. If set, the gateway "
            "uses min(timeout_seconds, max_query_seconds) as the enforced timeout — "
            "use this to give a specific call a tighter budget than the tool's default."
        ),
    )
    max_output_bytes: int | None = Field(
        default=None, description="Max size of the tool's output payload in bytes."
    )


class ToolContract(BaseModel):
    """Full contract a tool must satisfy to be registered with the gateway."""

    name: str = Field(description="Unique tool name, e.g. 'query_dataframe'.")
    purpose: str = Field(description="One-line description of what the tool does.")

    input_schema: Type[BaseModel] = Field(description="Pydantic model validating tool input.")
    output_schema: Type[BaseModel] = Field(description="Pydantic model validating tool output.")

    permission: Permission = Field(description="Access level required to invoke this tool.")
    limits: ToolLimits = Field(default_factory=ToolLimits)
    timeout_seconds: float = Field(default=30.0, description="Hard timeout for the call.")

    source_requirements: list[str] = Field(
        default_factory=list,
        description="Data sources/connectors this tool needs access to, e.g. ['duckdb'].",
    )
    failure_behavior: FailureBehavior = Field(default=FailureBehavior.RETURN_ERROR)

    handler: Callable[..., Any] = Field(
        description="The actual callable implementing the tool. Invoked only by the gateway."
    )

    model_config = {"arbitrary_types_allowed": True}
