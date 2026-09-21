last updated: 2026-09-21

# execution-backend — Tasks

- [x] Review legacy `core/execution.py` against blocklist requirements
- [x] Define `ExecutionBackend` interface
- [x] `LocalExecutor` implementation (allowed libs only, blocklist enforced)
- [x] Timeout / resource limits
- [ ] Register with tool-gateway (contract built via `gateway_adapter.py`; actual `gateway.register(...)` call left to server.py wiring)
