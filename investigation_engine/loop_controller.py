"""Investigation loop controller.

Wraps InvestigationState + InvestigationStore to enforce the bounded
loop: max iterations, max queries, timeout, and duplicate-query
protection (so the agent can't re-run the same query and burn budget).
Tools call this rather than mutating InvestigationState directly.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from investigation_engine.persistence import InvestigationStore, get_default_store
from investigation_engine.state import (
    Bounds,
    InvestigationState,
    InvestigationStatus,
    Query,
)


class BoundsExceededError(Exception):
    """Raised when a caller tries to keep going past the loop's bounds."""


class DuplicateQueryError(Exception):
    """Raised when a query identical to one already run is attempted again."""


def hash_query(source_id: str, query_text: str) -> str:
    normalized = f"{source_id}::{query_text.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


class InvestigationLoopController:
    def __init__(self, store: Optional[InvestigationStore] = None):
        self.store = store or get_default_store()

    # -- lifecycle ------------------------------------------------------
    def start(self, question: str, bounds: Optional[Bounds] = None) -> InvestigationState:
        state = InvestigationState.new(question, bounds=bounds)
        self.store.save(state)
        return state

    def load(self, investigation_id: str) -> Optional[InvestigationState]:
        return self.store.load(investigation_id)

    def save(self, state: InvestigationState) -> None:
        self.store.save(state)

    # -- bounded loop -----------------------------------------------------
    def _seconds_elapsed(self, state: InvestigationState) -> float:
        started = datetime.fromisoformat(state.created_at)
        return (datetime.now(timezone.utc) - started).total_seconds()

    def is_timed_out(self, state: InvestigationState) -> bool:
        return self._seconds_elapsed(state) >= state.bounds.timeout_seconds

    def should_stop(self, state: InvestigationState) -> bool:
        """True if the loop must stop for any reason (over bounds, timed
        out, or already resolved)."""
        return (
            state.status in (InvestigationStatus.COMPLETE, InvestigationStatus.ENOUGH_EVIDENCE, InvestigationStatus.STOPPED_LIMIT)
            or state.is_over_bounds()
            or self.is_timed_out(state)
        )

    def begin_iteration(self, state: InvestigationState) -> InvestigationState:
        """Call at the top of each investigation loop iteration. Raises
        BoundsExceededError (and marks the state stopped) if the loop
        should not continue."""
        if self.is_timed_out(state):
            state.status = InvestigationStatus.STOPPED_LIMIT
            self.store.save(state)
            raise BoundsExceededError(f"Investigation {state.id} timed out")
        if state.is_over_bounds():
            state.status = InvestigationStatus.STOPPED_LIMIT
            self.store.save(state)
            raise BoundsExceededError(f"Investigation {state.id} exceeded iteration/query bounds")

        state.iteration_count += 1
        self.store.save(state)
        return state

    def record_query(self, state: InvestigationState, source_id: str, query_text: str) -> Query:
        """Register a new query against a source, enforcing dup protection
        and the max_queries bound."""
        if len(state.queries) >= state.bounds.max_queries:
            state.status = InvestigationStatus.STOPPED_LIMIT
            self.store.save(state)
            raise BoundsExceededError(f"Investigation {state.id} hit max_queries")

        q_hash = hash_query(source_id, query_text)
        if state.is_duplicate_query(q_hash):
            raise DuplicateQueryError(f"Query already run against {source_id}: {query_text!r}")

        query = Query(id=f"qry_{q_hash}", source_id=source_id, query=query_text)
        state.queries.append(query)
        state.register_query_hash(q_hash)
        self.store.save(state)
        return query

    def check_evidence_sufficiency(self, state: InvestigationState) -> InvestigationState:
        """Call after evidence is added. Marks the investigation
        ENOUGH_EVIDENCE if the bound is met, so the caller knows to stop
        gathering and move to findings/conclusion."""
        if state.has_enough_evidence() and state.status == InvestigationStatus.ACTIVE:
            state.status = InvestigationStatus.ENOUGH_EVIDENCE
            self.store.save(state)
        return state

    def complete(self, state: InvestigationState) -> InvestigationState:
        state.status = InvestigationStatus.COMPLETE
        self.store.save(state)
        return state
