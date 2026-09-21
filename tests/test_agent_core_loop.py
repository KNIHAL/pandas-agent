"""Tests for agent_core.loop.AgentLoop — the plan/select-tool/execute/observe
cycle, using fake LLMProvider and ToolExecutor doubles (no real network,
no tool_gateway import — the loop is deliberately decoupled from both).
"""

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from agent_core.context import ConversationContext
from agent_core.llm_provider import LLMProvider
from agent_core.loop import AgentLoop, AgentLoopError
from agent_core.messages import LLMResponse, Role, ToolCallRequest, ToolSpec


class FakeLLMProvider(LLMProvider):
    """Returns pre-scripted responses in order; records every call it received."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, messages, tools=None, *, system=None, max_tokens=4096, temperature=0.0):
        self.calls.append({
            "messages": list(messages),
            "tools": tools,
            "system": system,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        if not self._responses:
            raise AssertionError("FakeLLMProvider ran out of scripted responses")
        return self._responses.pop(0)


class FakeToolExecutor:
    """Returns a pre-registered result per tool name; records every call."""

    def __init__(self, results: dict[str, object]) -> None:
        self._results = results
        self.calls: list[tuple[str, dict]] = []

    def invoke(self, tool_name, raw_input):
        self.calls.append((tool_name, raw_input))
        if tool_name not in self._results:
            raise AssertionError(f"No fake result registered for tool '{tool_name}'")
        return self._results[tool_name]


def ok(data):
    return SimpleNamespace(success=True, data=data, error=None)


def failed(message):
    return SimpleNamespace(success=False, data=None, error=SimpleNamespace(message=message))


# ---------------------------------------------------------------------------
# Happy path — no tool calls needed
# ---------------------------------------------------------------------------

def test_returns_immediately_when_no_tool_calls():
    provider = FakeLLMProvider([LLMResponse(content="the answer is 42")])
    executor = FakeToolExecutor({})
    loop = AgentLoop(provider, executor)
    ctx = ConversationContext(system="be helpful")
    ctx.add_user("what is the answer?")

    final = loop.run(ctx)

    assert final.content == "the answer is 42"
    assert final.role == Role.ASSISTANT
    assert len(provider.calls) == 1
    assert executor.calls == []
    # context now holds: user, assistant(final)
    assert [m.role for m in ctx.history()] == [Role.USER, Role.ASSISTANT]


def test_passes_system_tools_and_generation_params_to_provider():
    provider = FakeLLMProvider([LLMResponse(content="ok")])
    executor = FakeToolExecutor({})
    tools = [ToolSpec(name="echo", description="Echo.", parameters={"type": "object"})]
    loop = AgentLoop(provider, executor, tools=tools, max_tokens=123, temperature=0.5)
    ctx = ConversationContext(system="be helpful")
    ctx.add_user("hi")

    loop.run(ctx)

    call = provider.calls[0]
    assert call["system"] == "be helpful"
    assert call["tools"] == tools
    assert call["max_tokens"] == 123
    assert call["temperature"] == 0.5


# ---------------------------------------------------------------------------
# One tool-call round trip
# ---------------------------------------------------------------------------

def test_single_tool_call_round_trip():
    call = ToolCallRequest(id="c1", name="echo", arguments={"text": "hi"})
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use"),
        LLMResponse(content="done: HELLO"),
    ])
    executor = FakeToolExecutor({"echo": ok("HELLO")})
    loop = AgentLoop(provider, executor)
    ctx = ConversationContext()
    ctx.add_user("echo hi")

    final = loop.run(ctx)

    assert final.content == "done: HELLO"
    assert len(provider.calls) == 2
    assert executor.calls == [("echo", {"text": "hi"})]

    roles = [m.role for m in ctx.history()]
    assert roles == [Role.USER, Role.ASSISTANT, Role.TOOL, Role.ASSISTANT]

    tool_msg = ctx.history()[2]
    assert tool_msg.tool_call_id == "c1"
    assert tool_msg.name == "echo"
    assert tool_msg.content == "HELLO"


def test_multiple_tool_calls_in_one_response_are_all_executed_in_order():
    calls = [
        ToolCallRequest(id="c1", name="echo", arguments={"text": "a"}),
        ToolCallRequest(id="c2", name="echo", arguments={"text": "b"}),
    ]
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=calls, stop_reason="tool_use"),
        LLMResponse(content="done"),
    ])
    executor = FakeToolExecutor({"echo": ok("RESULT")})
    loop = AgentLoop(provider, executor)
    ctx = ConversationContext()
    ctx.add_user("go")

    loop.run(ctx)

    assert executor.calls == [("echo", {"text": "a"}), ("echo", {"text": "b"})]
    tool_msgs = [m for m in ctx.history() if m.role == Role.TOOL]
    assert [m.tool_call_id for m in tool_msgs] == ["c1", "c2"]


def test_failed_tool_result_becomes_error_content():
    call = ToolCallRequest(id="c1", name="echo", arguments={})
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use"),
        LLMResponse(content="recovered"),
    ])
    executor = FakeToolExecutor({"echo": failed("permission denied")})
    loop = AgentLoop(provider, executor)
    ctx = ConversationContext()
    ctx.add_user("go")

    loop.run(ctx)

    tool_msg = [m for m in ctx.history() if m.role == Role.TOOL][0]
    assert tool_msg.content == "ERROR: permission denied"


# ---------------------------------------------------------------------------
# max_iterations
# ---------------------------------------------------------------------------

def test_raises_agent_loop_error_when_max_iterations_exceeded():
    call = ToolCallRequest(id="c1", name="echo", arguments={})
    # Every response asks for another tool call — never a final answer.
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use")
        for _ in range(3)
    ])
    executor = FakeToolExecutor({"echo": ok("x")})
    loop = AgentLoop(provider, executor, max_iterations=3)
    ctx = ConversationContext()
    ctx.add_user("loop forever")

    with pytest.raises(AgentLoopError):
        loop.run(ctx)


def test_run_level_max_iterations_overrides_constructor_default():
    call = ToolCallRequest(id="c1", name="echo", arguments={})
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use")
    ])
    executor = FakeToolExecutor({"echo": ok("x")})
    loop = AgentLoop(provider, executor, max_iterations=10)
    ctx = ConversationContext()
    ctx.add_user("go")

    with pytest.raises(AgentLoopError):
        loop.run(ctx, max_iterations=1)


# ---------------------------------------------------------------------------
# _stringify / result-to-content conversions
# ---------------------------------------------------------------------------

class _Point(BaseModel):
    x: int
    y: int


@pytest.mark.parametrize(
    "data,expected",
    [
        (None, ""),
        ("already a string", "already a string"),
        ({"a": 1}, '{"a": 1}'),
        ([1, 2, 3], "[1, 2, 3]"),
        (42, "42"),
    ],
)
def test_stringify_handles_common_data_shapes(data, expected):
    assert AgentLoop._stringify(data) == expected


def test_stringify_handles_pydantic_model():
    result = AgentLoop._stringify(_Point(x=1, y=2))
    assert result == _Point(x=1, y=2).model_dump_json()


def test_result_to_content_uses_data_when_result_has_no_success_attribute():
    # A bare value with no .success/.data/.error is treated as the data itself.
    assert AgentLoop._result_to_content("plain string result") == "plain string result"
