"""Domain errors for data-catalog."""

from __future__ import annotations


class AuthorityConflictError(Exception):
    """Raised when upserting an entry would claim authority over a metric
    that another entry already holds, without force=True."""

    def __init__(self, metric_name: str, current_entry_id: int) -> None:
        super().__init__(
            f"Metric '{metric_name}' is already authoritative under entry id {current_entry_id}. "
            f"Pass force=True to reassign."
        )
        self.metric_name = metric_name
        self.current_entry_id = current_entry_id


class EntryNotFoundError(Exception):
    pass
