"""ORM model for finalized artifacts (artifacts-visualization).

Per spec.md's flow: Source -> Working Dataset -> Analysis -> Finalized
Dataset/Artifact. The files generate_chart/export_dataset/generate_report
write are "working" output; a record here is what makes one of those
outputs a "finalized" artifact worth keeping and revisiting later.

`generator_config` stores exactly what's needed to reproduce the artifact
(e.g. {"chart_type": "bar", "columns": [...]} for a chart, or
{"format": "csv", "data": [...]} for an export) so a later regenerate call
can rebuild the file from the same analysis result -- no re-analysis.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ArtifactRecord(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)

    artifact_type: Mapped[str] = mapped_column(String(32), index=True)  # chart/csv/excel/pdf/report
    title: Mapped[str] = mapped_column(String(256))
    file_path: Mapped[str] = mapped_column(String(1024))

    generator_config: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=lambda: dt.datetime.now(dt.UTC))
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=lambda: dt.datetime.now(dt.UTC), onupdate=lambda: dt.datetime.now(dt.UTC)
    )

    def to_summary(self) -> dict:
        return {
            "id": self.id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail(self) -> dict:
        return {**self.to_summary(), "generator_config": self.generator_config}
