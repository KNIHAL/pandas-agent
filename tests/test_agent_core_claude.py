"""Tests for agent_core.providers.claude — translation logic + complete()
with a mocked anthropic client (no real network call, no API key needed).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from anthropic.types import Message as AnthropicMessage
from anthropic.types import TextBlock, ToolUseBlock, Usage as AnthropicUsage

from agent_core.llm_provider import LLMProviderError
from agent_core.messages import Message, Role, ToolCallRequest, ToolSpec
from agent_core.providers.claude import (
    ClaudeProvider,
    _from_anthropic_response,
    _to_anthropic_messages,
    _to_anthropic_tools,
)


# ---------------------------------------------------------------------------
# _to_anthropic_messages
# ---------------------------------------------------------------------------

def test_to_anthropic_messages_maps_user_message():
    out = _to_anthropic_messages([Message(role=Role.USER, content="hi")])
    assert out == [{"role": "user", "content": "hi"}]


def test_to_anthropic_messages_maps_assistant_text():
    out = _to_anthropic_messages([Message(role=Role.ASSISTANT, content="hello back")])
    assert out == [{"role": "assistant", "content": "hello back"}]


def test_to_anthropic_messages_maps_assistant_tool_calls():
    call = ToolCallRequest(id="toolu_1", name="echo", arguments={"text": "hi"})
    out = _to_anthropic_messages([Message(role=Role.ASSISTANT, tool_calls=[call])])
    assert out == [{
        "role": "assistant",
        "content": [{"type": "tool_use", "id": "toolu_1", "name": "echo", "input": {"text": "hi"}}],
    }]


def test_to_anthropic_messages_maps_tool_result():
    msg = Message(role=Role.TOOL, content="HELLO", tool_call_id="toolu_1", name="echo")
    out = _to_anthropic_messages([msg])
    assert out == [{
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "HELLO"}],
    }]


def test_to_anthropic_messages_skips_system_messages():
    out = _to_anthropic_messages([
        Message(role=Role.SYSTEM, content="you are a helper"),
        Message(role=Role.USER, content="hi"),
    ])
    assert out == [{"role": "user", "content": "hi"}]


# ---------------------------------------------------------------------------
# _to_anthropic_tools
# ---------------------------------------------------------------------------

def test_to_anthropic_tools_none_when_no_tools():
    assert _to_anthropic_tools(None) is None
    assert _to_anthropic_tools([]) is None


def test_to_anthropic_tools_builds_tool_dicts():
    tools = [ToolSpec(name="echo", description="Echo it.", parameters={"type": "object"})]
    out = _to_anthropic_tools(tools)
    assert out == [{"name": "echo", "description": "Echo it.", "input_schema": {"type": "object"}}]


# ---------------------------------------------------------------------------
# _from_anthropic_response
# ---------------------------------------------------------------------------

def _make_response(*, content, stop_reason="end_turn", input_tokens=10, output_tokens=5):
    return AnthropicMessage(
        id="msg_1",
        type="message",
        role="assistant",
        model="claude-sonnet-4-6",
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=AnthropicUsage(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_from_anthropic_response_text_only():
    resp = _make_response(content=[TextBlock(type="text", text="hello there")])
    result = _from_anthropic_response(resp)
    assert result.content == "hello there"
    assert result.tool_calls == []
    assert result.stop_reason == "end_turn"
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_from_anthropic_response_with_tool_use():
    block = ToolUseBlock(id="toolu_1", input={"text": "hi"}, name="echo", type="tool_use")
    resp = _make_response(content=[block], stop_reason="tool_use")
    result = _from_anthropic_response(resp)
    assert result.content is None
    assert result.stop_reason == "tool_use"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "toolu_1"
    assert result.tool_calls[0].name == "echo"
    assert result.tool_calls[0].arguments == {"text": "hi"}


def test_from_anthropic_response_max_tokens():
    resp = _make_response(content=[TextBlock(type="text", text="cut off")], stop_reason="max_tokens")
    result = _from_anthropic_response(resp)
    assert result.stop_reason == "max_tokens"


def test_from_anthropic_response_stop_sequence_maps_to_end_turn():
    resp = _make_response(content=[TextBlock(type="text", text="done")], stop_reason="stop_sequence")
    result = _from_anthropic_response(resp)
    assert result.stop_reason == "end_turn"


def test_from_anthropic_response_mixed_text_and_tool_use():
    text_block = TextBlock(type="text", text="Let me check that.")
    tool_block = ToolUseBlock(id="toolu_1", input={"text": "hi"}, name="echo", type="tool_use")
    resp = _make_response(content=[text_block, tool_block], stop_reason="tool_use")
    result = _from_anthropic_response(resp)
    assert result.content == "Let me check that."
    assert len(result.tool_calls) == 1


# ---------------------------------------------------------------------------
# ClaudeProvider.complete() with a mocked client
# ---------------------------------------------------------------------------

def test_complete_returns_llm_response_on_success():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response(
        content=[TextBlock(type="text", text="hi back")]
    )
    provider = ClaudeProvider(client=mock_client, model="claude-sonnet-4-6")

    result = provider.complete([Message(role=Role.USER, content="hi")])

    assert result.content == "hi back"
    mock_client.messages.create.assert_called_once()
    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert "tools" not in kwargs  # no tools passed -> key omitted, not None


def test_complete_passes_system_and_tools_when_given():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_response(
        content=[TextBlock(type="text", text="ok")]
    )
    provider = ClaudeProvider(client=mock_client)
    tools = [ToolSpec(name="echo", description="Echo.", parameters={"type": "object"})]

    provider.complete([Message(role=Role.USER, content="hi")], tools=tools, system="be helpful")

    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["system"] == "be helpful"
    assert kwargs["tools"] == [{"name": "echo", "description": "Echo.", "input_schema": {"type": "object"}}]


def test_complete_wraps_sdk_exception_in_llm_provider_error():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("network is down")
    provider = ClaudeProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])


def test_complete_wraps_response_parsing_failure_in_llm_provider_error():
    mock_client = MagicMock()
    # missing .content triggers an AttributeError inside _from_anthropic_response
    mock_client.messages.create.return_value = SimpleNamespace(stop_reason="end_turn")
    provider = ClaudeProvider(client=mock_client)

    with pytest.raises(LLMProviderError):
        provider.complete([Message(role=Role.USER, content="hi")])
