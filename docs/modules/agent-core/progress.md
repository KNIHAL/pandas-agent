last updated: 2026-09-20

# agent-core — Progress

Branch `feature/agent-core`, created off `feature/tool-gateway` (agent-core
needs to import `tool_gateway`, which isn't merged to the base branch yet).

- `agent_core/messages.py` — `Role`, `Message`, `ToolCallRequest`, `ToolSpec`,
  `Usage`, `LLMResponse` (pydantic v2). Provider-agnostic wire types; no
  provider SDK types leak past the adapter boundary.
- `agent_core/llm_provider.py` — abstract `LLMProvider.complete()` + `LLMProviderError`
  (adapters must wrap SDK exceptions in this).
- Tests: `tests/test_agent_core_messages.py`, 12/12 passing.
- `agent_core/providers/gemini.py` — `GeminiProvider`, backed by the new
  `google-genai` SDK (NOT the deprecated `google-generativeai` package).
  Translation kept as standalone functions (`_to_gemini_contents`,
  `_to_gemini_tools`, `_from_gemini_response`) so they're unit-testable
  without a network call. `complete()` wraps every SDK/parsing exception in
  `LLMProviderError`.
- Tests: `tests/test_agent_core_gemini.py`, 13/13 passing, all against a
  mocked `genai.Client` — no API key needed/used.
- `agent_core/providers/claude.py` — `ClaudeProvider`, backed by the `anthropic`
  SDK. Same translation-as-standalone-functions pattern as Gemini
  (`_to_anthropic_messages`, `_to_anthropic_tools`, `_from_anthropic_response`).
  Notable: `tools`/`system` kwargs are only added to the request dict when
  non-empty (Anthropic's SDK expects them omitted, not `None`).
- Tests: `tests/test_agent_core_claude.py`, 16/16 passing, mocked
  `anthropic.Anthropic` client — no API key needed.
- `agent_core/providers/groq_provider.py` — `GroqProvider`, backed by the
  `groq` SDK (OpenAI-compatible chat completions). File named
  `groq_provider.py`, not `groq.py`, to avoid shadowing the `groq` package
  inside its own package folder. Unlike Gemini/Claude, Groq has a native
  "system" role, so SYSTEM messages translate directly instead of being
  dropped. Tool-call arguments come back as a JSON string (not a dict) —
  parsed with a malformed-JSON fallback to `{}`.
- Tests: `tests/test_agent_core_groq.py`, 16/16 passing, mocked `groq.Groq`
  client — no API key needed.
- `agent_core/context.py` — `ConversationContext`: system prompt + message
  history, `add_user`/`add_assistant`/`add_tool_result` helpers,
  `history()` (returns a copy), `trim(max_messages)` (basic message-count
  trim, V1 — no token counting, no tool_use/tool_result pairing
  preservation across the trim boundary).
- `agent_core/loop.py` — `AgentLoop.run(context)`: plan (LLMProvider.complete)
  → if no tool_calls, return the final assistant Message → else execute
  every tool_call via a `ToolExecutor` (structural Protocol: anything with
  `.invoke(tool_name, raw_input)`), append each result as a TOOL message,
  repeat. Raises `AgentLoopError` past `max_iterations`. Deliberately does
  NOT import tool_gateway — `ToolGateway.invoke` already matches
  `ToolExecutor` structurally, so the "Hook into Tool Gateway" task should
  need no adapter, just building the `list[ToolSpec]` from
  `ToolContract`s and passing a `ToolGateway` instance as the executor.
- `agent_core/gateway_adapter.py` — the only agent_core file that imports
  `tool_gateway`. `tool_spec_from_contract(contract)` builds a `ToolSpec`
  (name, purpose→description, `input_schema.model_json_schema()`→parameters).
  `tool_specs_from_gateway(gateway)` builds the full list for every
  registered tool. `ToolGateway` needed no adapter to act as an
  `AgentLoop` `ToolExecutor` — confirmed via `isinstance(gateway, ToolExecutor)`
  (the Protocol is `runtime_checkable`).
- Added `ToolGateway.get_contract(name)` (small addition on the tool-gateway
  side) so the adapter can look up contracts by name; `list_tools()` alone
  only returned names.
- Tests: `tests/test_agent_core_gateway_adapter.py` (6/6) — spec-building,
  the Protocol check, and two end-to-end `AgentLoop` runs against a *real*
  `ToolGateway` (only the LLM side is faked): one happy path, one where a
  denied permission surfaces as an `ERROR:` tool message the model can see
  and recover from.
- Module complete. 134/134 tests passing repo-wide.
- Next module per STATUS.md: pick from execution-backend, data-catalog,
  connectors, investigation-engine, artifacts-visualization, desktop-app.
