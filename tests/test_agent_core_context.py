"""Tests for agent_core.context.ConversationContext."""

import pytest

from agent_core.context import ConversationContext
from agent_core.messages import Role, ToolCallRequest


def test_starts_empty_with_optional_system():
    ctx = ConversationContext(system="be helpful")
    assert ctx.system == "be helpful"
    assert ctx.history() == []


def test_add_user_appends_user_message():
    ctx = ConversationContext()
    msg = ctx.add_user("hi")
    assert msg.role == Role.USER
    assert msg.content == "hi"
    assert ctx.history() == [msg]


def test_add_assistant_text_only():
    ctx = ConversationContext()
    msg = ctx.add_assistant(content="hello back")
    assert msg.role == Role.ASSISTANT
    assert msg.content == "hello back"
    assert msg.tool_calls == []


def test_add_assistant_with_tool_calls():
    ctx = ConversationContext()
    call = ToolCallRequest(id="c1", name="echo", arguments={"text": "hi"})
    msg = ctx.add_assistant(tool_calls=[call])
    assert msg.content is None
    assert msg.tool_calls == [call]


def test_add_tool_result():
    ctx = ConversationContext()
    msg = ctx.add_tool_result(tool_call_id="c1", name="echo", content="HELLO")
    assert msg.role == Role.TOOL
    assert msg.tool_call_id == "c1"
    assert msg.name == "echo"
    assert msg.content == "HELLO"


def test_history_returns_a_copy_not_the_live_list():
    ctx = ConversationContext()
    ctx.add_user("hi")
    snapshot = ctx.history()
    ctx.add_user("second")
    assert len(snapshot) == 1
    assert len(ctx.history()) == 2


def test_clear_empties_messages_but_keeps_system():
    ctx = ConversationContext(system="be helpful")
    ctx.add_user("hi")
    ctx.clear()
    assert ctx.history() == []
    assert ctx.system == "be helpful"


def test_trim_keeps_only_most_recent_messages():
    ctx = ConversationContext()
    for i in range(5):
        ctx.add_user(f"msg {i}")
    ctx.trim(2)
    assert [m.content for m in ctx.history()] == ["msg 3", "msg 4"]


def test_trim_noop_when_under_limit():
    ctx = ConversationContext()
    ctx.add_user("only one")
    ctx.trim(10)
    assert len(ctx.history()) == 1


def test_trim_to_zero_clears_everything():
    ctx = ConversationContext()
    ctx.add_user("hi")
    ctx.trim(0)
    assert ctx.history() == []


def test_trim_rejects_negative_max_messages():
    ctx = ConversationContext()
    with pytest.raises(ValueError):
        ctx.trim(-1)


def test_constructor_accepts_initial_messages_list():
    ctx = ConversationContext()
    ctx.add_user("first")
    ctx2 = ConversationContext(messages=ctx.history())
    ctx2.add_user("second")
    assert len(ctx.history()) == 1
    assert len(ctx2.history()) == 2
