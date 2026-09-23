"""Investigation State schema.

Chain: Question -> Intent -> Sources -> Queries -> Observations ->
Hypotheses -> Tests -> Evidence -> Findings -> Conclusion -> Artifacts

Purpose: follow-up questions don't redo full analysis -- the whole
chain is persisted and can be reloaded/extended.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class InvestigationStatus(str, Enum):
    ACTIVE = "active"
    ENOUGH_EVIDENCE = "enough_evidence"
    STOPPED_LIMIT = "stopped_limit"
    COMPLETE = "complete"


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    TESTING = "testing"
    SUPPORTED = "supported"
    REJECTED = "rejected"


@dataclass
class Intent:
    metric: Optional[str] = None
    period: Optional[str] = None
    comparison: Optional[str] = None
    type: Optional[str] = None  # e.g. "root-cause"


@dataclass
class Source:
    id: str
    name: str
    authoritative: bool = False


@dataclass
class Query:
    id: str
    source_id: str
    query: str
    result_summary: Optional[str] = None
    created_at: str = field(default_factory=_now)


@dataclass
class Observation:
    id: str
    query_id: Optional[str]
    description: str
    data: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)


@dataclass
class Hypothesis:
    id: str
    statement: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    created_at: str = field(default_factory=_now)


@dataclass
class Test:
    id: str
    hypothesis_id: str
    description: str
    passed: Optional[bool] = None
    created_at: str = field(default_factory=_now)


@dataclass
class Evidence:
    id: str
    test_id: Optional[str]
    description: str
    contribution_pct: Optional[float] = None
    created_at: str = field(default_factory=_now)


@dataclass
class Finding:
    id: str
    statement: str
    evidence_ids: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class Conclusion:
    summary: Optional[str] = None
    finding_ids: list[str] = field(default_factory=list)


@dataclass
class Bounds:
    max_iterations: int = 8
    max_queries: int = 20
    timeout_seconds: int = 300
    min_evidence_items: int = 1


@dataclass
class InvestigationState:
    id: str
    question: str
    intent: Intent = field(default_factory=Intent)
    sources: list[Source] = field(default_factory=list)
    queries: list[Query] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    tests: list[Test] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    conclusion: Conclusion = field(default_factory=Conclusion)
    artifact_ids: list[str] = field(default_factory=list)
    bounds: Bounds = field(default_factory=Bounds)
    status: InvestigationStatus = InvestigationStatus.ACTIVE
    iteration_count: int = 0
    seen_query_hashes: set[str] = field(default_factory=set)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    @classmethod
    def new(cls, question: str, bounds: Optional[Bounds] = None) -> "InvestigationState":
        return cls(id=_new_id("inv"), question=question, bounds=bounds or Bounds())

    def touch(self) -> None:
        self.updated_at = _now()

    # -- bounded-loop checks -------------------------------------------------
    def is_duplicate_query(self, query_hash: str) -> bool:
        return query_hash in self.seen_query_hashes

    def register_query_hash(self, query_hash: str) -> None:
        self.seen_query_hashes.add(query_hash)

    def has_enough_evidence(self) -> bool:
        return len(self.evidence) >= self.bounds.min_evidence_items

    def is_over_bounds(self) -> bool:
        return (
            self.iteration_count >= self.bounds.max_iterations
            or len(self.queries) >= self.bounds.max_queries
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["seen_query_hashes"] = list(self.seen_query_hashes)
        d["status"] = self.status.value
        for h in d["hypotheses"]:
            h["status"] = HypothesisStatus(h["status"]).value if not isinstance(h["status"], str) else h["status"]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InvestigationState":
        d = dict(d)
        d["seen_query_hashes"] = set(d.get("seen_query_hashes", []))
        d["status"] = InvestigationStatus(d["status"])
        d["intent"] = Intent(**d.get("intent", {}))
        d["sources"] = [Source(**s) for s in d.get("sources", [])]
        d["queries"] = [Query(**q) for q in d.get("queries", [])]
        d["observations"] = [Observation(**o) for o in d.get("observations", [])]
        hyps = []
        for h in d.get("hypotheses", []):
            h = dict(h)
            h["status"] = HypothesisStatus(h["status"])
            hyps.append(Hypothesis(**h))
        d["hypotheses"] = hyps
        d["tests"] = [Test(**t) for t in d.get("tests", [])]
        d["evidence"] = [Evidence(**e) for e in d.get("evidence", [])]
        d["findings"] = [Finding(**f) for f in d.get("findings", [])]
        d["conclusion"] = Conclusion(**d.get("conclusion", {}))
        d["bounds"] = Bounds(**d.get("bounds", {}))
        return cls(**d)
