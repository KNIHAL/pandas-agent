"""Read/write operations for the finalized-artifacts store."""
from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from .errors import ArtifactNotFoundError
from .models import ArtifactRecord


class ArtifactRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def finalize(self, *, artifact_type: str, title: str, file_path: str, generator_config: dict) -> dict:
        with self._session_factory() as session:
            record = ArtifactRecord(
                artifact_type=artifact_type,
                title=title,
                file_path=file_path,
                generator_config=generator_config,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return record.to_detail()

    def get(self, artifact_id: int) -> dict:
        with self._session_factory() as session:
            record = session.get(ArtifactRecord, artifact_id)
            if record is None:
                raise ArtifactNotFoundError(artifact_id)
            return record.to_detail()

    def list(self, artifact_type: str | None = None) -> list[dict]:
        with self._session_factory() as session:
            query = session.query(ArtifactRecord)
            if artifact_type is not None:
                query = query.filter_by(artifact_type=artifact_type)
            records = query.order_by(ArtifactRecord.created_at.desc()).all()
            return [r.to_summary() for r in records]
