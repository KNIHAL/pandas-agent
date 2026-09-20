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
- Next: Groq adapter — one at a time, each fully tested before the next.
  No live-API testing here (no keys configured); live testing is Kumar's
  call once he has keys set.
