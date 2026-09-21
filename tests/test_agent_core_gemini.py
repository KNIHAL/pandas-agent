"""Tests for agent_core.providers.gemini — translation logic + complete()
with a mocked google-genai client (no real network call, no API key needed).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.genai import types as gtypes

from agent_core.llm_provider import LLMProviderError
from agent_core.messages import Message, Role, ToolCallRequest, ToolSpec
from agent_core.providers.gemini import (
    GeminiProvider,
    _from_gemini_response,
    _to_gemini_contents,
    _to_gemini_tools,
)


# ---------------------------------------------------------------------------
# _to_gemini_contents
# ---------------------------------------------------------------------------

def test_to_gemini_contents_maps_user_message():
    contents = _to_gemini_contents([Message(role=Role.USER, content="hi")])
    assert len(contents) == 1
    assert contents[0].role == "user"
    assert contents[0].parts[0].text == "hi"


def test_to_gemini_contents_maps_assistant_text_to_model_role():
    contents = _to_gemini_contents([Message(role=Role.ASSISTANT, content="hello back")])
    assert contents[0].role == "model"
    assert contents[0].parts[0].text == "hello back"


def test_to_gemini_contents_maps_assistant_tool_calls_to_function_call_parts():
    call = ToolCallRequest(id="c1", name="echo", arguments={"text": "hi"})
    contents = _to_gemini_contents([Message(role=Role.ASSISTANT, tool_calls=[call])])
    assert contents[0].role == "model"
    fc = contents[0].parts[0].function_call
    assert fc.name == "echo"
    assert dict(fc.args) == {"text": "hi"}


def test_to_gemini_contents_maps_tool_result_to_function_response():
    msg = Message(role=Role.TOOL, content="HELLO", tool_call_id="c1", name="echo")
    contents = _to_gemini_contents([msg])
    assert contents[0].role == "user"
    fr = contents[0].parts[0].function_response
    assert fr.name == "echo"
    assert fr.response == {"result": "HELLO"}


def test_to_gemini_contents_skips_system_messages():
    contents = _to_gemini_contents([
        Message(role=Role.SYSTEM, content="you are a helper"),
        Message(role=Role.USER, content="hi"),
    ])
    assert len(contents) == 1
    assert contents[0].role == "user"


# ---------------------------------------------------------------------------
# _to_gemini_tools
# ---------------------------------------------------------------------------

def test_to_gemini_tools_none_when_no_tools():
    assert _to_gemini_tools(None) is None
    assert _to_gemini_tools([]) is None


def test_to_gemini_tools_builds_function_declarations():
    tools = [ToolSpec(name="echo", description="Echo it.", parameters={"type": "object"})]
    result = _to_gemini_tools(tools)
    assert len(result) == 1
    decl = result[0].function_declarations[0]
    assert decl.name == "echo"
    assert decl.description == "Echo it."


# ---------------------------------------------------------------------------
# _from_gemini_response
# ---------------------------------------------------------------------------

def _make_response(*, parts, finish_reason="STOP", prompt_tokens=10, output_tokens=5):
    candidate = gtypes.Candidate(
        content=gtypes.Content(role="model", parts=parts),
        finish_reason=finish_reason,
    )
    return gtypes.GenerateContentResponse(
        candidates=[candidate],
        usage_metadata=gtypes.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt_tokens, candidates_token_count=output_tokens
        ),
        model_version="gemini-2.0-flash",
    )


def test_from_gemini_response_text_only():
    resp = _make_response(parts=[gtypes.Part.from_text(text="hello there")])
    result = _from_gemini_response(resp)
    assert result.content == "hello there"
    assert result.tool_calls == []
    assert result.stop_reason == "end_turn"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_from_gemini_response_with_function_call():
    resp = _make_response(parts=[gtypes.Part.from_function_call(name="echo", args={"text": "hi"})])
    result = _from_gemini_response(resp)
    assert result.content is None
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "echo"
    assert result.tool_calls[0].arguments == {"text": "hi"}


def test_from_gemini_response_max_tokens():
    resp = _make_response(parts=[gtypes.Part.from_text(text="cut off")], finish_reason="MAX_TOKENS")
    result = _from_gemini_response(resp)
    assert result.stop_reason == "max_tokens"


# ---------------------------------------------------------------------------
# GeminiProvider.complete() with a mocked client
# ---------------------------------------------------------------------------

def test_complete_returns_llm_response_on_success():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_response(
        parts=[gtypes.Part.from_text(text="hi back")]
    )
    provider = GeminiProvider(client=mock_client, model="gemini-2.0-flash")

    result = provider.complete([Message(role=Role.USER, content="hi")])

    assert result.content == "hi back"
    mock_client.models.generate_content.assert_called_once()
    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.0-flash"


def test_complete_wraps_sdk_exception_in_llm_provider_error():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("network is down")
    provider = GeminiProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])


def test_complete_wraps_response_parsing_failure_in_llm_provider_error():
    mock_client = MagicMock()
    # candidates=[] triggers an IndexError inside _from_gemini_response
    mock_client.models.generate_content.return_value = SimpleNamespace(candidates=[])
    provider = GeminiProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])
