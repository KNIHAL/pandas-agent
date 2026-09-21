"""Tests for agent_core.gateway_adapter — building ToolSpecs from a real
ToolGateway, and an end-to-end AgentLoop run using a real ToolGateway as
the tool_executor (only the LLM side is faked).
"""

from pydantic import BaseModel

from agent_core.context import ConversationContext
from agent_core.gateway_adapter import tool_spec_from_contract, tool_specs_from_gateway
from agent_core.llm_provider import LLMProvider
from agent_core.loop import AgentLoop, ToolExecutor
from agent_core.messages import LLMResponse, Message, Role, ToolCallRequest
from tool_gateway import Permission, ToolContract, ToolGateway


class EchoIn(BaseModel):
    text: str


class EchoOut(BaseModel):
    text: str


def echo_handler(inp: EchoIn) -> EchoOut:
    return EchoOut(text=inp.text.upper())


def make_gateway(tmp_path) -> ToolGateway:
    from tool_gateway import AuditLogger

    gw = ToolGateway(
        granted_permissions={Permission.READ_DATA},
        audit_logger=AuditLogger(tmp_path / "audit.jsonl"),
    )
    gw.register(ToolContract(
        name="echo",
        purpose="Echo text back, uppercased.",
        input_schema=EchoIn,
        output_schema=EchoOut,
        permission=Permission.READ_DATA,
        handler=echo_handler,
    ))
    return gw


# ---------------------------------------------------------------------------
# tool_spec_from_contract / tool_specs_from_gateway
# ---------------------------------------------------------------------------

def test_tool_spec_from_contract_uses_name_purpose_and_json_schema(tmp_path):
    gw = make_gateway(tmp_path)
    contract = gw.get_contract("echo")

    spec = tool_spec_from_contract(contract)

    assert spec.name == "echo"
    assert spec.description == "Echo text back, uppercased."
    assert spec.parameters == EchoIn.model_json_schema()


def test_tool_specs_from_gateway_builds_all_registered_tools(tmp_path):
    gw = make_gateway(tmp_path)
    gw.register(ToolContract(
        name="shout", purpose="Shout it.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))

    specs = tool_specs_from_gateway(gw)

    assert {s.name for s in specs} == {"echo", "shout"}


def test_tool_specs_from_gateway_empty_when_no_tools_registered(tmp_path):
    from tool_gateway import AuditLogger
    gw = ToolGateway(audit_logger=AuditLogger(tmp_path / "audit.jsonl"))
    assert tool_specs_from_gateway(gw) == []


# ---------------------------------------------------------------------------
# ToolGateway satisfies the ToolExecutor Protocol with no adapter
# ---------------------------------------------------------------------------

def test_tool_gateway_satisfies_tool_executor_protocol(tmp_path):
    gw = make_gateway(tmp_path)
    assert isinstance(gw, ToolExecutor)


# ---------------------------------------------------------------------------
# End-to-end: AgentLoop + real ToolGateway (LLM side faked)
# ---------------------------------------------------------------------------

class FakeLLMProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []

    def complete(self, messages, tools=None, *, system=None, max_tokens=4096, temperature=0.0):
        self.calls.append({"messages": list(messages), "tools": tools})
        return self._responses.pop(0)


def test_end_to_end_agent_loop_with_real_tool_gateway(tmp_path):
    gw = make_gateway(tmp_path)
    tools = tool_specs_from_gateway(gw)

    call = ToolCallRequest(id="c1", name="echo", arguments={"text": "hi"})
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use"),
        LLMResponse(content="Tool said: HI"),
    ])

    loop = AgentLoop(provider, gw, tools=tools)
    ctx = ConversationContext(system="You can call the echo tool.")
    ctx.add_user("echo 'hi' for me")

    final = loop.run(ctx)

    assert final.content == "Tool said: HI"
    # the tool result the gateway produced (a pydantic EchoOut) got stringified
    # to JSON before being appended as the TOOL message
    tool_msg = [m for m in ctx.history() if m.role == Role.TOOL][0]
    assert tool_msg.content == EchoOut(text="HI").model_dump_json()


def test_end_to_end_agent_loop_surfaces_gateway_permission_denied_as_error_content(tmp_path):
    from tool_gateway import AuditLogger
    gw = ToolGateway(granted_permissions=set(), audit_logger=AuditLogger(tmp_path / "audit.jsonl"))
    gw.register(ToolContract(
        name="echo", purpose="Echo.", input_schema=EchoIn, output_schema=EchoOut,
        permission=Permission.READ_DATA, handler=echo_handler,
    ))
    tools = tool_specs_from_gateway(gw)

    call = ToolCallRequest(id="c1", name="echo", arguments={"text": "hi"})
    provider = FakeLLMProvider([
        LLMResponse(content=None, tool_calls=[call], stop_reason="tool_use"),
        LLMResponse(content="I couldn't do that."),
    ])

    loop = AgentLoop(provider, gw, tools=tools)
    ctx = ConversationContext()
    ctx.add_user("echo 'hi' for me")

    final = loop.run(ctx)

    assert final.content == "I couldn't do that."
    tool_msg = [m for m in ctx.history() if m.role == Role.TOOL][0]
    assert tool_msg.content.startswith("ERROR:")
    assert "permission" in tool_msg.content.lower()
