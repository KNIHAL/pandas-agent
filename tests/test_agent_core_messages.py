"""Tests for agent_core.messages and agent_core.llm_provider — shape/defaults,
and that LLMProvider can't be instantiated without implementing complete().
"""

import pytest
from pydantic import ValidationError

from agent_core.llm_provider import LLMProvider
from agent_core.messages import (
    LLMResponse,
    Message,
    Role,
    ToolCallRequest,
    ToolSpec,
    Usage,
)


def test_message_defaults():
    msg = Message(role=Role.USER, content="hi")
    assert msg.role == Role.USER
    assert msg.content == "hi"
    assert msg.tool_calls == []
    assert msg.tool_call_id is None
    assert msg.name is None


def test_message_accepts_string_role():
    # Providers/tests often build these from plain dicts — string role should coerce.
    msg = Message(role="assistant", content="ok")
    assert msg.role == Role.ASSISTANT


def test_message_with_tool_calls():
    call = ToolCallRequest(id="call_1", name="echo", arguments={"text": "hi"})
    msg = Message(role=Role.ASSISTANT, tool_calls=[call])
    assert msg.content is None
    assert msg.tool_calls[0].name == "echo"


def test_tool_result_message_shape():
    msg = Message(role=Role.TOOL, content="HELLO", tool_call_id="call_1", name="echo")
    assert msg.role == Role.TOOL
    assert msg.tool_call_id == "call_1"
    assert msg.name == "echo"


def test_tool_call_request_requires_all_fields():
    with pytest.raises(ValidationError):
        ToolCallRequest(id="call_1", name="echo")  # missing arguments


def test_tool_spec_minimal():
    spec = ToolSpec(name="echo", description="Echo text.", parameters={"type": "object"})
    assert spec.name == "echo"
    assert spec.parameters == {"type": "object"}


def test_llm_response_defaults():
    resp = LLMResponse(content="hello")
    assert resp.content == "hello"
    assert resp.tool_calls == []
    assert resp.stop_reason == "end_turn"
    assert resp.usage == Usage(input_tokens=0, output_tokens=0)
    assert resp.raw == {}


def test_llm_response_with_tool_calls_and_usage():
    resp = LLMResponse(
        content=None,
        tool_calls=[ToolCallRequest(id="c1", name="echo", arguments={})],
        stop_reason="tool_use",
        usage=Usage(input_tokens=10, output_tokens=5),
        raw={"id": "resp_1"},
    )
    assert resp.stop_reason == "tool_use"
    assert resp.usage.input_tokens == 10
    assert resp.raw["id"] == "resp_1"


def test_llm_response_rejects_invalid_stop_reason():
    with pytest.raises(ValidationError):
        LLMResponse(content="hi", stop_reason="not_a_real_reason")


def test_llm_provider_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        LLMProvider()


def test_llm_provider_subclass_must_implement_complete():
    class IncompleteProvider(LLMProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()


def test_llm_provider_subclass_with_complete_can_be_instantiated():
    class WorkingProvider(LLMProvider):
        def complete(self, messages, tools=None, *, system=None, max_tokens=4096, temperature=0.0):
            return LLMResponse(content="ok")

    provider = WorkingProvider()
    result = provider.complete([Message(role=Role.USER, content="hi")])
    assert result.content == "ok"
