"""ORM models for the data-catalog module.

Schema follows spec.md's field list: source, entity, table, fields, metrics,
dimensions, date fields, authority, freshness, relationships, permissions,
lineage.

MetricAuthority is a separate table (not a column on CatalogEntry) so "which
source wins per metric" is enforced by a DB-level unique constraint on
metric_name — at most one authoritative entry per metric, always, not just
by convention.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CatalogEntry(Base):
    __tablename__ = "catalog_entries"
    __table_args__ = (UniqueConstraint("source", "entity", "table_name", name="uq_source_entity_table"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    source: Mapped[str] = mapped_column(String(128), index=True)
    entity: Mapped[str] = mapped_column(String(128), index=True)
    table_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    fields: Mapped[list] = mapped_column(JSON, default=list)
    metrics: Mapped[list] = mapped_column(JSON, default=list)
    dimensions: Mapped[list] = mapped_column(JSON, default=list)
    date_fields: Mapped[list] = mapped_column(JSON, default=list)

    authority: Mapped[bool] = mapped_column(Boolean, default=False)
    freshness: Mapped[dict] = mapped_column(JSON, default=dict)
    relationships: Mapped[list] = mapped_column(JSON, default=list)
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)
    lineage: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.UTC), onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    metric_authorities: Mapped[list["MetricAuthority"]] = relationship(back_populates="entry")

    def to_summary(self) -> dict:
        return {
            "source": self.source,
            "entity": self.entity,
            "table": self.table_name,
            "authority": self.authority,
            "metrics": self.metrics,
        }

    def to_detail(self) -> dict:
        return {
            **self.to_summary(),
            "fields": self.fields,
            "dimensions": self.dimensions,
            "date_fields": self.date_fields,
            "freshness": self.freshness,
            "relationships": self.relationships,
            "permissions": self.permissions,
            "lineage": self.lineage,
        }


class MetricAuthority(Base):
    """metric_name -> the single CatalogEntry authoritative for it."""

    __tablename__ = "metric_authority"

    metric_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("catalog_entries.id"), nullable=False)

    entry: Mapped["CatalogEntry"] = relationship(back_populates="metric_authorities")
