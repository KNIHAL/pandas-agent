last updated: 2026-09-20

# tool-gateway — Progress

- Branch `feature/tool-gateway` created off `docs/project-setup`.
- Code lives in `tool_gateway/` (underscore, not kebab — Python can't import hyphenated package names; see DECISIONS.md). Docs folder stays `docs/modules/tool-gateway/` (kebab, matches repo/module naming).
- Contract schema done: `tool_gateway/contracts.py` — `ToolContract` (pydantic v2), `Permission`, `ToolLimits`, `FailureBehavior`.
- Gateway core done: `tool_gateway/gateway.py` (`ToolGateway.invoke`) — permission check → input validation → timeout-bound execution (ThreadPoolExecutor, RETRY_ONCE support) → output validation → row-limit truncation hook → audit log. `tool_gateway/audit.py` — JSONL audit logger.
- Tests: `tests/test_tool_gateway.py`, 5/5 passing (happy path, invalid input, permission denied, timeout, not found).
- Next: permission enforcement is done as part of gateway core — remaining tasks are query/row-limit enforcement hardening (currently just a `truncate()` convention hook) and richer failure-surface shaping for agent-core.
