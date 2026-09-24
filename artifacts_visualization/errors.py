"""Domain errors for artifacts-visualization."""
from __future__ import annotations


class ArtifactNotFoundError(Exception):
    def __init__(self, artifact_id: int) -> None:
        super().__init__(f"No finalized artifact found with id {artifact_id}.")
        self.artifact_id = artifact_id
