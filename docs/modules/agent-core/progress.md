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
- Next: Gemini adapter, then Claude adapter, then Groq adapter — one at a
  time, each fully tested before the next (same discipline as tool-gateway).
  Real adapters won't be live-API-tested here (no keys configured in this
  environment) — tested against a `FakeLLMProvider`/mocked SDK response
  instead; live testing is Kumar's call once he has keys set.
