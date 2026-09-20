"""Groq adapter for LLMProvider, backed by the `groq` SDK (OpenAI-compatible
chat completions API).

Translation logic (`_to_groq_messages` / `_to_groq_tools` /
`_from_groq_response`) is kept as standalone functions so it's
unit-testable without a real API call — only `complete()` touches the
network.

Unlike Gemini/Claude, Groq's wire format has a native "system" role, so
SYSTEM-role Messages are translated directly rather than dropped; the
`system` kwarg (if given) is additionally prepended as its own system
message.
"""

from __future__ import annotations

import json
from typing import Any

import groq

from ..llm_provider import LLMProvider, LLMProviderError
from ..messages import LLMResponse, Message, Role, ToolCallRequest, ToolSpec, Usage

_FINISH_REASON_MAP = {
    "stop": "end_turn",
    "length": "max_tokens",
    "tool_calls": "tool_use",
}


def _to_groq_messages(messages: list[Message], system: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if system:
        out.append({"role": "system", "content": system})

    for msg in messages:
        if msg.role == Role.SYSTEM:
            out.append({"role": "system", "content": msg.content or ""})

        elif msg.role == Role.USER:
            out.append({"role": "user", "content": msg.content or ""})

        elif msg.role == Role.ASSISTANT:
            if msg.tool_calls:
                out.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                        }
                        for tc in msg.tool_calls
                    ],
                })
            else:
                out.append({"role": "assistant", "content": msg.content or ""})

        elif msg.role == Role.TOOL:
            out.append({"role": "tool", "tool_call_id": msg.tool_call_id, "content": msg.content or ""})

    return out


def _to_groq_tools(tools: list[ToolSpec] | None) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    return [
        {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
        for t in tools
    ]


def _from_groq_response(response: Any) -> LLMResponse:
    choice = response.choices[0]
    message = choice.message

    tool_calls: list[ToolCallRequest] = []
    for tc in (message.tool_calls or []):
        try:
            args = json.loads(tc.function.arguments) if tc.function.arguments else {}
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(ToolCallRequest(id=tc.id, name=tc.function.name, arguments=args))

    if tool_calls:
        stop_reason = "tool_use"
    else:
        stop_reason = _FINISH_REASON_MAP.get(choice.finish_reason or "", "end_turn")

    usage_obj = getattr(response, "usage", None)
    usage = Usage(
        input_tokens=getattr(usage_obj, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage_obj, "completion_tokens", 0) or 0,
    )

    return LLMResponse(
        content=message.content,
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        usage=usage,
        raw={"id": getattr(response, "id", None), "model": getattr(response, "model", None)},
    )


class GroqProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
        client: groq.Groq | None = None,
    ) -> None:
        self._model = model
        self._client = client or groq.Groq(api_key=api_key)

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
            "messages": _to_groq_messages(messages, system=system),
        }
        tool_dicts = _to_groq_tools(tools)
        if tool_dicts:
            kwargs["tools"] = tool_dicts

        try:
            response = self._client.chat.completions.create(**kwargs)
        except LLMProviderError:
            raise
        except Exception as e:  # noqa: BLE001 - adapter boundary, wrap everything
            raise LLMProviderError(f"Groq call failed: {e}") from e

        try:
            return _from_groq_response(response)
        except Exception as e:  # noqa: BLE001
            raise LLMProviderError(f"Failed to parse Groq response: {e}") from e
