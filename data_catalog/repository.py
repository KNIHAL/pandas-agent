"""Query/write operations for the catalog.

Full-table-scan filtering is used for find_data(): catalog entries are
metadata about data sources (tables/entities), not the data itself, so even
an enterprise catalog is expected to stay in the low thousands of rows —
this stays simple and correct rather than reaching for SQLite FTS5
prematurely. Revisit if that assumption stops holding.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from .errors import AuthorityConflictError, EntryNotFoundError
from .models import CatalogEntry, MetricAuthority


class CatalogRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    # -- writes -----------------------------------------------------------

    def upsert_entry(
        self,
        *,
        source: str,
        entity: str,
        table_name: str | None = None,
        fields: list[str] | None = None,
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
        date_fields: list[str] | None = None,
        authority: bool = False,
        freshness: dict | None = None,
        relationships: list[dict] | None = None,
        permissions: dict | None = None,
        lineage: str | None = None,
        force_authority: bool = False,
    ) -> dict:
        metrics = metrics or []

        with self._session_factory() as session:
            entry = (
                session.query(CatalogEntry)
                .filter_by(source=source, entity=entity, table_name=table_name)
                .one_or_none()
            )
            if entry is None:
                entry = CatalogEntry(source=source, entity=entity, table_name=table_name)
                session.add(entry)

            entry.fields = fields or []
            entry.metrics = metrics
            entry.dimensions = dimensions or []
            entry.date_fields = date_fields or []
            entry.authority = authority
            entry.freshness = freshness or {}
            entry.relationships = relationships or []
            entry.permissions = permissions or {}
            entry.lineage = lineage

            session.flush()  # assigns entry.id if new

            if authority:
                for metric_name in metrics:
                    existing = session.get(MetricAuthority, metric_name)
                    if existing is not None and existing.entry_id != entry.id and not force_authority:
                        session.rollback()
                        raise AuthorityConflictError(metric_name, existing.entry_id)
                    if existing is None:
                        session.add(MetricAuthority(metric_name=metric_name, entry_id=entry.id))
                    else:
                        existing.entry_id = entry.id

            session.commit()
            return entry.to_detail()

    # -- reads --------------------------------------------------------------

    def list_sources(self) -> list[str]:
        with self._session_factory() as session:
            rows = session.query(CatalogEntry.source).distinct().order_by(CatalogEntry.source).all()
            return [row[0] for row in rows]

    def inspect_source(self, source: str) -> list[dict]:
        with self._session_factory() as session:
            entries = session.query(CatalogEntry).filter_by(source=source).order_by(CatalogEntry.entity).all()
            if not entries:
                raise EntryNotFoundError(f"No catalog entries found for source '{source}'.")
            return [e.to_summary() for e in entries]

    def inspect_schema(self, source: str, entity: str) -> list[dict]:
        with self._session_factory() as session:
            entries = (
                session.query(CatalogEntry)
                .filter_by(source=source, entity=entity)
                .order_by(CatalogEntry.table_name)
                .all()
            )
            if not entries:
                raise EntryNotFoundError(f"No catalog entry for source='{source}', entity='{entity}'.")
            return [e.to_detail() for e in entries]

    def find_data(self, query: str) -> list[dict]:
        needle = query.strip().lower()
        with self._session_factory() as session:
            entries = session.query(CatalogEntry).all()

        def matches(e: CatalogEntry) -> bool:
            haystacks = [e.source, e.entity, e.table_name or ""]
            haystacks += e.fields + e.metrics + e.dimensions
            return any(needle in h.lower() for h in haystacks)

        return [e.to_summary() for e in entries if matches(e)]

    def resolve_authority(self, metric_name: str) -> dict | None:
        with self._session_factory() as session:
            link = session.get(MetricAuthority, metric_name)
            if link is None:
                return None
            entry = session.get(CatalogEntry, link.entry_id)
            return entry.to_summary() if entry else None
