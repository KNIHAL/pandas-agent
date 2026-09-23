"""Investigation State persistence.

Redis-backed by default (per spec: "likely Redis"), with an in-memory
store as a drop-in fallback so the module works and is fully testable
without a live Redis instance. Swappable via the InvestigationStore
interface.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional

from investigation_engine.state import InvestigationState

DEFAULT_TTL_SECONDS = 60 * 60 * 24  # 24h


class InvestigationStore(ABC):
    """Persistence interface for InvestigationState."""

    @abstractmethod
    def save(self, state: InvestigationState) -> None:
        ...

    @abstractmethod
    def load(self, investigation_id: str) -> Optional[InvestigationState]:
        ...

    @abstractmethod
    def delete(self, investigation_id: str) -> None:
        ...


class InMemoryInvestigationStore(InvestigationStore):
    """Process-local store. Used as default / test fallback."""

    def __init__(self) -> None:
        self._data: dict[str, dict] = {}

    def save(self, state: InvestigationState) -> None:
        state.touch()
        self._data[state.id] = state.to_dict()

    def load(self, investigation_id: str) -> Optional[InvestigationState]:
        raw = self._data.get(investigation_id)
        return InvestigationState.from_dict(raw) if raw is not None else None

    def delete(self, investigation_id: str) -> None:
        self._data.pop(investigation_id, None)


class RedisInvestigationStore(InvestigationStore):
    """Redis-backed store. Requires a redis client (redis-py).

    Key layout: investigation:{id} -> JSON blob, with a TTL so
    abandoned investigations don't leak memory in Redis.
    """

    def __init__(self, redis_client, ttl_seconds: int = DEFAULT_TTL_SECONDS, key_prefix: str = "investigation:"):
        self._redis = redis_client
        self._ttl = ttl_seconds
        self._prefix = key_prefix

    def _key(self, investigation_id: str) -> str:
        return f"{self._prefix}{investigation_id}"

    def save(self, state: InvestigationState) -> None:
        state.touch()
        payload = json.dumps(state.to_dict(), default=str)
        self._redis.set(self._key(state.id), payload, ex=self._ttl)

    def load(self, investigation_id: str) -> Optional[InvestigationState]:
        payload = self._redis.get(self._key(investigation_id))
        if payload is None:
            return None
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        return InvestigationState.from_dict(json.loads(payload))

    def delete(self, investigation_id: str) -> None:
        self._redis.delete(self._key(investigation_id))


def get_default_store() -> InvestigationStore:
    """Best-effort Redis store, falling back to in-memory if unavailable.

    Kept simple on purpose: callers needing guaranteed Redis should
    construct RedisInvestigationStore themselves with a live client.
    """
    try:
        import redis  # type: ignore

        client = redis.Redis()
        client.ping()
        return RedisInvestigationStore(client)
    except Exception:
        return InMemoryInvestigationStore()
