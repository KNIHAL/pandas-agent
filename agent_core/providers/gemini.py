"""Gemini adapter for LLMProvider, backed by the `google-genai` SDK.

Translation logic (`_to_gemini_contents` / `_from_gemini_response`) is kept
as standalone functions so it can be unit-tested without a real API call —
only `complete()` itself touches the network.
"""

from __future__ import annotations

from typing import Any

from google import genai
from google.genai import types as gtypes

from ..llm_provider import LLMProvider, LLMProviderError
from ..messages import LLMResponse, Message, Role, ToolCallRequest, ToolSpec, Usage

_FINISH_REASON_MAP = {
    "STOP": "end_turn",
    "MAX_TOKENS": "max_tokens",
}


def _to_gemini_contents(messages: list[Message]) -> list[gtypes.Content]:
    """Convert provider-agnostic messages into Gemini `Content` objects.

    Gemini has no "system" role in `contents` (system prompts go through
    `GenerateContentConfig.system_instruction`) and no "tool" role — a tool
    result is sent back as a `user`-role Content containing a
    `function_response` Part. Any SYSTEM messages found here (as opposed to
    the `system=` kwarg on `complete()`) are dropped; callers should prefer
    the `system` kwarg.
    """
    contents: list[gtypes.Content] = []
    for msg in messages:
        if msg.role == Role.SYSTEM:
            continue

        if msg.role == Role.USER:
            contents.append(gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=msg.content or "")]))

        elif msg.role == Role.ASSISTANT:
            if msg.tool_calls:
                parts = [
                    gtypes.Part.from_function_call(name=tc.name, args=tc.arguments)
                    for tc in msg.tool_calls
                ]
            else:
                parts = [gtypes.Part.from_text(text=msg.content or "")]
            contents.append(gtypes.Content(role="model", parts=parts))

        elif msg.role == Role.TOOL:
            contents.append(gtypes.Content(
                role="user",
                parts=[gtypes.Part.from_function_response(
                    name=msg.name or "",
                    response={"result": msg.content},
                )],
            ))
    return contents


def _to_gemini_tools(tools: list[ToolSpec] | None) -> list[gtypes.Tool] | None:
    if not tools:
        return None
    declarations = [
        gtypes.FunctionDeclaration(name=t.name, description=t.description, parameters=t.parameters)
        for t in tools
    ]
    return [gtypes.Tool(function_declarations=declarations)]


def _from_gemini_response(response: Any) -> LLMResponse:
    candidate = response.candidates[0]
    text_parts: list[str] = []
    tool_calls: list[ToolCallRequest] = []

    for i, part in enumerate(candidate.content.parts or []):
        fc = getattr(part, "function_call", None)
        if fc is not None:
            tool_calls.append(ToolCallRequest(id=f"call_{i}", name=fc.name, arguments=dict(fc.args or {})))
        elif getattr(part, "text", None):
            text_parts.append(part.text)

    raw_finish_reason = getattr(candidate, "finish_reason", None)
    finish_reason = getattr(raw_finish_reason, "value", raw_finish_reason) or ""

    if tool_calls:
        stop_reason = "tool_use"
    else:
        stop_reason = _FINISH_REASON_MAP.get(finish_reason, "end_turn")

    usage_meta = getattr(response, "usage_metadata", None)
    usage = Usage(
        input_tokens=getattr(usage_meta, "prompt_token_count", 0) or 0,
        output_tokens=getattr(usage_meta, "candidates_token_count", 0) or 0,
    )

    return LLMResponse(
        content="\n".join(text_parts) if text_parts else None,
        tool_calls=tool_calls,
        stop_reason=stop_reason,
        usage=usage,
        raw={"model_version": getattr(response, "model_version", None)},
    )


class GeminiProvider(LLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.0-flash",
        client: genai.Client | None = None,
    ) -> None:
        self._model = model
        self._client = client or genai.Client(api_key=api_key)

    def complete(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        *,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> LLMResponse:
        try:
            contents = _to_gemini_contents(messages)
            config = gtypes.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max_tokens,
                temperature=temperature,
                tools=_to_gemini_tools(tools),
            )
            response = self._client.models.generate_content(
                model=self._model, contents=contents, config=config
            )
        except LLMProviderError:
            raise
        except Exception as e:  # noqa: BLE001 - adapter boundary, wrap everything
            raise LLMProviderError(f"Gemini call failed: {e}") from e

        try:
            return _from_gemini_response(response)
        except Exception as e:  # noqa: BLE001
            raise LLMProviderError(f"Failed to parse Gemini response: {e}") from e
