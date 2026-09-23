"""Mixpanel connector -- Query API (mixpanel.com/api/query) +
Export API (data.mixpanel.com/api/2.0/export), auth via a Mixpanel
service account (username + secret, HTTP Basic auth) and a project_id.

An entity is an event name (e.g. "Purchase") -- its raw event occurrences
are the rows, event properties are the columns (flattened; keys vary per
event so schema/columns are sampled, not fixed). filters supports
{"start_date": ..., "end_date": ...} (default: last 7 days, "YYYY-MM-DD")
plus any other key as an exact-match property filter, applied client-side
after export since the raw Export API has no generic property filter.

No live Mixpanel project was available to test against, so this is
verified against a mocked HTTP layer -- see
tests/test_connectors_mixpanel.py. Swap in a real service account and it
should work unchanged; re-verify against a live project before relying
on it.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_QUERY_BASE = "https://mixpanel.com/api/query"
_EXPORT_BASE = "https://data.mixpanel.com/api/2.0/export"


class MixpanelConnector(Connector):
    name = "mixpanel"

    def __init__(self, service_account_username: str, service_account_secret: str, project_id: str) -> None:
        self._auth = (service_account_username, service_account_secret)
        self._project_id = project_id

    def test_connection(self) -> bool:
        try:
            resp = requests.get(
                f"{_QUERY_BASE}/events/names",
                auth=self._auth,
                params={"type": "general", "project_id": self._project_id},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        resp = requests.get(
            f"{_QUERY_BASE}/events/names",
            auth=self._auth,
            params={"type": "general", "project_id": self._project_id},
            timeout=10,
        )
        resp.raise_for_status()
        return sorted(resp.json())

    def _export(self, entity: str, start_date: str, end_date: str) -> list[dict]:
        resp = requests.get(
            _EXPORT_BASE,
            auth=self._auth,
            params={
                "from_date": start_date,
                "to_date": end_date,
                "event": json.dumps([entity]),
                "project_id": self._project_id,
            },
            timeout=30,
        )
        if resp.status_code == 404:
            raise EntityNotFoundError(f"No Mixpanel event '{entity}' (or no data in range).")
        resp.raise_for_status()
        rows = []
        for line in resp.text.strip().splitlines():
            if not line:
                continue
            raw = json.loads(line)
            props = raw.get("properties", {})
            row = {"event": raw.get("event"), "time": props.get("time"), "distinct_id": props.get("distinct_id")}
            row.update({k: v for k, v in props.items() if k not in ("time", "distinct_id")})
            rows.append(row)
        return rows

    def get_schema(self, entity: str) -> dict:
        end = date.today()
        start = end - timedelta(days=7)
        rows = self._export(entity, start.isoformat(), end.isoformat())
        fields: list[str] = ["event", "time", "distinct_id"]
        for row in rows:
            for k in row:
                if k not in fields:
                    fields.append(k)
        return {"fields": fields, "field_types": {f: "string" for f in fields}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        filters = dict(filters or {})
        end = filters.pop("end_date", date.today().isoformat())
        start = filters.pop("start_date", (date.today() - timedelta(days=7)).isoformat())

        rows = self._export(entity, start, end)
        df = pd.DataFrame(rows)
        if filters:
            for col, val in filters.items():
                df = df[df[col] == val]
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
