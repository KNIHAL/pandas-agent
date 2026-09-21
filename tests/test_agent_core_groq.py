"""Tests for agent_core.providers.groq_provider — translation logic +
complete() with a mocked groq client (no real network call, no API key
needed).
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from agent_core.llm_provider import LLMProviderError
from agent_core.messages import Message, Role, ToolCallRequest, ToolSpec
from agent_core.providers.groq_provider import (
    GroqProvider,
    _from_groq_response,
    _to_groq_messages,
    _to_groq_tools,
)


# ---------------------------------------------------------------------------
# _to_groq_messages
# ---------------------------------------------------------------------------

def test_to_groq_messages_maps_user_message():
    out = _to_groq_messages([Message(role=Role.USER, content="hi")])
    assert out == [{"role": "user", "content": "hi"}]


def test_to_groq_messages_maps_assistant_text():
    out = _to_groq_messages([Message(role=Role.ASSISTANT, content="hello back")])
    assert out == [{"role": "assistant", "content": "hello back"}]


def test_to_groq_messages_maps_assistant_tool_calls_with_json_string_arguments():
    call = ToolCallRequest(id="call_1", name="echo", arguments={"text": "hi"})
    out = _to_groq_messages([Message(role=Role.ASSISTANT, tool_calls=[call])])
    assert out == [{
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "call_1",
            "type": "function",
            "function": {"name": "echo", "arguments": json.dumps({"text": "hi"})},
        }],
    }]


def test_to_groq_messages_maps_tool_result():
    msg = Message(role=Role.TOOL, content="HELLO", tool_call_id="call_1", name="echo")
    out = _to_groq_messages([msg])
    assert out == [{"role": "tool", "tool_call_id": "call_1", "content": "HELLO"}]


def test_to_groq_messages_translates_system_role_messages_directly():
    # Groq (OpenAI-style) supports a native system role, unlike Gemini/Claude.
    out = _to_groq_messages([Message(role=Role.SYSTEM, content="you are a helper")])
    assert out == [{"role": "system", "content": "you are a helper"}]


def test_to_groq_messages_prepends_system_kwarg():
    out = _to_groq_messages([Message(role=Role.USER, content="hi")], system="be helpful")
    assert out[0] == {"role": "system", "content": "be helpful"}
    assert out[1] == {"role": "user", "content": "hi"}


# ---------------------------------------------------------------------------
# _to_groq_tools
# ---------------------------------------------------------------------------

def test_to_groq_tools_none_when_no_tools():
    assert _to_groq_tools(None) is None
    assert _to_groq_tools([]) is None


def test_to_groq_tools_builds_function_wrapped_dicts():
    tools = [ToolSpec(name="echo", description="Echo it.", parameters={"type": "object"})]
    out = _to_groq_tools(tools)
    assert out == [{
        "type": "function",
        "function": {"name": "echo", "description": "Echo it.", "parameters": {"type": "object"}},
    }]


# ---------------------------------------------------------------------------
# _from_groq_response
# ---------------------------------------------------------------------------

def _make_message(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _make_tool_call(id_, name, arguments_json):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=name, arguments=arguments_json))


def _make_response(*, message, finish_reason="stop", prompt_tokens=10, completion_tokens=5):
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return SimpleNamespace(choices=[choice], usage=usage, id="chatcmpl_1", model="llama-3.3-70b-versatile")


def test_from_groq_response_text_only():
    resp = _make_response(message=_make_message(content="hello there"))
    result = _from_groq_response(resp)
    assert result.content == "hello there"
    assert result.tool_calls == []
    assert result.stop_reason == "end_turn"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_from_groq_response_with_tool_call_parses_json_arguments():
    tc = _make_tool_call("call_1", "echo", json.dumps({"text": "hi"}))
    resp = _make_response(message=_make_message(tool_calls=[tc]), finish_reason="tool_calls")
    result = _from_groq_response(resp)
    assert result.content is None
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "echo"
    assert result.tool_calls[0].arguments == {"text": "hi"}


def test_from_groq_response_malformed_json_arguments_falls_back_to_empty_dict():
    tc = _make_tool_call("call_1", "echo", "{not valid json")
    resp = _make_response(message=_make_message(tool_calls=[tc]), finish_reason="tool_calls")
    result = _from_groq_response(resp)
    assert result.tool_calls[0].arguments == {}


def test_from_groq_response_length_finish_reason_maps_to_max_tokens():
    resp = _make_response(message=_make_message(content="cut off"), finish_reason="length")
    result = _from_groq_response(resp)
    assert result.stop_reason == "max_tokens"


# ---------------------------------------------------------------------------
# GroqProvider.complete() with a mocked client
# ---------------------------------------------------------------------------

def test_complete_returns_llm_response_on_success():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response(
        message=_make_message(content="hi back")
    )
    provider = GroqProvider(client=mock_client, model="llama-3.3-70b-versatile")

    result = provider.complete([Message(role=Role.USER, content="hi")])

    assert result.content == "hi back"
    mock_client.chat.completions.create.assert_called_once()
    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["model"] == "llama-3.3-70b-versatile"
    assert "tools" not in kwargs


def test_complete_passes_tools_and_system_when_given():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response(
        message=_make_message(content="ok")
    )
    provider = GroqProvider(client=mock_client)
    tools = [ToolSpec(name="echo", description="Echo.", parameters={"type": "object"})]

    provider.complete([Message(role=Role.USER, content="hi")], tools=tools, system="be helpful")

    _, kwargs = mock_client.chat.completions.create.call_args
    assert kwargs["messages"][0] == {"role": "system", "content": "be helpful"}
    assert kwargs["tools"][0]["function"]["name"] == "echo"


def test_complete_wraps_sdk_exception_in_llm_provider_error():
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("network is down")
    provider = GroqProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])


def test_complete_wraps_response_parsing_failure_in_llm_provider_error():
    mock_client = MagicMock()
    # empty choices triggers an IndexError inside _from_groq_response
    mock_client.chat.completions.create.return_value = SimpleNamespace(choices=[])
    provider = GroqProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])
