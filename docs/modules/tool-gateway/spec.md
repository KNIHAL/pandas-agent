last updated: 2026-09-20

# tool-gateway — Spec

## What
- Sits between Agent and all Tools (LLM never gets uncontrolled direct access to 40-50 tools).
- Enforces: permissions, input validation, query limits, row limits, timeout, source access, audit logging, action boundaries, failure handling.
- Every tool registered here needs a contract: name, purpose, input schema, output schema, permission, limits, timeout, source requirements, failure behavior.

## Boundaries
- All other modules' tools (data access, execution, connectors, investigation, artifacts) get exposed to agent-core only through this gateway.
