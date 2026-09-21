last updated: 2026-09-20

# tool-gateway — Progress

Module complete. Branch `feature/tool-gateway` off `docs/project-setup`.

Code lives in `tool_gateway/` (snake_case — Python can't import hyphenated
package names; docs folder stays `docs/modules/tool-gateway/` kebab-case,
see DECISIONS.md).

Files:
- `tool_gateway/contracts.py` — `ToolContract` (pydantic v2), `Permission`,
  `ToolLimits`, `FailureBehavior`.
- `tool_gateway/errors.py` — typed exceptions (`ToolNotFoundError`,
  `PermissionDeniedError`, `InvalidInputError`, `ToolTimeoutError`,
  `ToolExecutionError`, `OutputValidationError`, `OutputTooLargeError`), all
  subclassing `ToolGatewayError`; `exception_for(error_type, message)` maps
  a ToolError.type string to its typed exception.
- `tool_gateway/audit.py` — thread-safe append-only JSONL `AuditLogger`.
- `tool_gateway/gateway.py` — `ToolGateway.invoke()` pipeline:
  1. permission check
  2. input validation against `input_schema`
  3. timeout-bound execution (`min(timeout_seconds, limits.max_query_seconds)`),
     `RETRY_ONCE` retries the handler once on any exception
  4. output validation against `output_schema` (accepts either a schema
     instance or a plain dict from the handler)
  5. `limits.max_rows` truncation via an output-model `truncate(n)` convention
     (audit-logged with `extra: {"truncated": true}`); `limits.max_output_bytes`
     checked after truncation, via `model_dump_json()` size
  6. every outcome (success or failure) is audit-logged
  7. `failure_behavior` is honored uniformly across every failure path —
     `RETURN_ERROR` (default) returns a `ToolResult(success=False, error=...)`,
     `RAISE` raises the typed exception (chained `from` the original cause
     where there is one)

Tests (44/44 passing): `tests/test_contracts.py`, `tests/test_errors.py`,
`tests/test_audit.py` (incl. a concurrency test), `tests/test_gateway.py`
(permission grant/revoke, retry, timeout vs max_query_seconds, row/byte
limits interacting, RAISE vs RETURN_ERROR for every failure type).

Next module per STATUS.md: agent-core (or whichever is picked up next) will
call `ToolGateway.invoke()` rather than tool handlers directly.
