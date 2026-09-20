"""Claude adapter for LLMProvider, backed by the `anthropic` SDK.

Translation logic (`_to_anthropic_messages` / `_to_anthropic_tools` /
`_from_anthropic_response`) is kept as standalone functions so it's
unit-testable without a real API call — only `complete()` touches the
network.
"""

from __future__ import annotations

from typing import Any

import anthropic

from ..llm_provider import LLMProvider, LLMProviderError
from ..messages import LLMResponse, Message, Role, ToolCallRequest, ToolSpec, Usage

_STOP_REASON_MAP = {
    "end_turn": "end_turn",
    "stop_sequence": "end_turn",
    "max_tokens": "max_tokens",
    "tool_use": "tool_use",
}


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert provider-agnostic messages into Anthropic's message dicts.

    Anthropic has no "system" role in `messages` (it's a separate top-level
    `system` param on the API call) — SYSTEM messages found here are
    dropped; callers should prefer the `system` kwarg on `complete()`.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == Role.SYSTEM:
            continue

        if msg.role == Role.USER:
            out.append({"role": "user", "content": msg.content or ""})

        elif msg.role == Role.ASSISTANT:
            if msg.tool_calls:
                out.append({
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                        for tc in msg.tool_calls
                    ],
                })
            else:
                out.append({"role": "assistant", "content": msg.content or ""})

        elif msg.role == Role.TOOL:
            out.append({
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": msg.tool_call_id, "content": msg.content or ""}
                ],
            })
    return out


def _to_anthropic_tools(tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    return [
        {"name": t.name, "description": t.description, "input_schema": t.parameters}
        for t in tools
    ]


def _from_anthropic_response(response: Any) -> LLMResponse:
    text_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []

    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(ToolCallRequest(id=block.id, name=block.name, arguments=dict(block.input or {})))

    stop_reason = _STOP_REASON_MAP.get(response.stop_reason or "", "end_turn")

    usage = Usage(
        input_tokens=getattr(response.usage, "input_tokens", 0) or 0,
        output_tokens=getattr(response.usage, "output_tokens", 0) or 0,
    )

    return LLMResponse(
        content="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        usage=usage,
        raw={"id": getattr(response, "id", None), "model": getattr(response, "model", None)},
    )


class ClaudeProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self._model = model
        self._client = client or anthropic.Anthropic(api_key=api_key)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": _to_anthropic_messages(messages),
        }
        if system:
            kwargs["system"] = system
        tool_dicts = _to_anthropic_tools(tools)
        if tool_dicts:
            kwargs["tools"] = tool_dicts

        try:
            response = self._client.messages.create(**kwargs)
        except LLMProviderError:
            raise
        except Exception as e:  # noqa: BLE001 - adapter boundary, wrap everything
            raise LLMProviderError(f"Claude call failed: {e}") from e

        try:
            return _from_anthropic_response(response)
        except Exception as e:  # noqa: BLE001
            raise LLMProviderError(f"Failed to parse Claude response: {e}") from e
