last updated: 2026-09-20

# execution-backend — Spec

## What
- Runs analytical code in a controlled environment (no raw unrestricted exec()).
- Interface: `ExecutionBackend` with `LocalExecutor` (V1), `DockerExecutor`/`VMExecutor`/`CauslyExecutor` (future).
- V1 = local controlled execution only.

## Allowed
- Pandas, NumPy, Matplotlib, DuckDB, approved stats libraries.

## Blocked
- shell/OS commands, subprocess, arbitrary network access, credential/env secret access, arbitrary external programs, package installation, modification of source databases.

## Note
- V1 local executor is NOT a hardened security sandbox — don't claim it is. Stronger isolation is future work.

## Legacy
- Old `core/execution.py` exists from CrewAI version — review it, reuse safe parts, don't assume it already meets the blocklist above.
