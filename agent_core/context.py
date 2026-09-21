"""Conversation Context — the message history + system prompt the agent
loop reads from and appends to each iteration.

V1 scope: an in-memory message list with helpers to append each message
kind correctly-shaped, plus a basic message-count trim. Token-aware
trimming and persistence are out of scope here (see investigation-engine
for the fuller Investigation State this will eventually sit inside).
"""

from __future__ import annotations

from .messages import Message, Role, ToolCallRequest


class ConversationContext:
    """Holds one conversation's system prompt + message history."""

    def __init__(self, system: str | None = None, messages: list[Message] | None = None) -> None:
        self.system = system
        self.messages: list[Message] = list(messages) if messages else []

    def add_user(self, content: str) -> Message:
        msg = Message(role=Role.USER, content=content)
        self.messages.append(msg)
        return msg

    def add_assistant(
        self, content: str | None = None, tool_calls: list[ToolCallRequest] | None = None
    ) -> Message:
        msg = Message(role=Role.ASSISTANT, content=content, tool_calls=tool_calls or [])
        self.messages.append(msg)
        return msg

    def add_tool_result(self, *, tool_call_id: str, name: str, content: str) -> Message:
        msg = Message(role=Role.TOOL, content=content, tool_call_id=tool_call_id, name=name)
        self.messages.append(msg)
        return msg

    def history(self) -> list[Message]:
        """A copy of the message list, safe for a provider call to consume."""
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()

    def trim(self, max_messages: int) -> None:
        """Keep only the most recent `max_messages` messages.

        Basic message-count trim for V1 — no token counting, no
        summarization of dropped turns. If the boundary would split a
        tool_use/tool_result pair, the pairing is not preserved; callers
        with strict provider pairing requirements should trim less
        aggressively or roll their own summarization upstream.
        """
        if max_messages < 0:
            raise ValueError("max_messages must be >= 0")
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:] if max_messages > 0 else []
