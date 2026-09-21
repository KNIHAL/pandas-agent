"""Glue between agent_core and tool_gateway.

This is the only file in agent_core that imports tool_gateway. AgentLoop
itself stays decoupled (see loop.py's ToolExecutor Protocol) — this module
just builds the list[ToolSpec] an LLMProvider needs from a ToolGateway's
registered contracts, and documents that ToolGateway needs no adapter to
act as an AgentLoop's ToolExecutor.
"""

from __future__ import annotations

from tool_gateway import ToolContract, ToolGateway

from .messages import ToolSpec


def tool_spec_from_contract(contract: ToolContract) -> ToolSpec:
    """Build the wire-format ToolSpec an LLMProvider needs from a ToolContract.

    - name: passed through as-is.
    - description: the contract's `purpose` (its one-line description).
    - parameters: JSON Schema from the contract's `input_schema`, via
      pydantic's `model_json_schema()`.
    """
    return ToolSpec(
        name=contract.name,
        description=contract.purpose,
        parameters=contract.input_schema.model_json_schema(),
    )


def tool_specs_from_gateway(gateway: ToolGateway) -> list[ToolSpec]:
    """Build ToolSpecs for every tool currently registered on `gateway`.

    Pass the result as AgentLoop(..., tools=...); pass `gateway` itself as
    the AgentLoop's tool_executor — ToolGateway.invoke(tool_name, raw_input)
    already matches the ToolExecutor Protocol, no wrapping needed.
    """
    specs = []
    for name in gateway.list_tools():
        contract = gateway.get_contract(name)
        if contract is not None:
            specs.append(tool_spec_from_contract(contract))
    return specs
