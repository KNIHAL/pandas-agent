"""Google Analytics 4 (GA4) connector -- Analytics Data API v1beta
(analyticsdata.googleapis.com), auth via a service-account JSON key (the
service account's email must be added as a Viewer on the GA4 property).

GA4 has no "tables" -- it's a report query API over dimensions and
metrics, not a fixed schema. Design choice to keep it inside the same
Connector interface rather than a bespoke one: an entity is a report spec
string "dim1,dim2|metric1,metric2" (e.g. "date,country|activeUsers,sessions"
-- see analyticsdata dimension/metric API names in GA4's docs). filters
supports {"start_date": ..., "end_date": ...} (default: last 30 days) plus
any other key as an exact-match dimension filter.

No live GA4 property was available to test against, so this is verified
against a mocked HTTP layer -- see tests/test_connectors_ga4.py. Swap in
a real service-account key + property ID and it should work unchanged;
re-verify against a live property before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .base import Connector
from .errors import EntityNotFoundError

_SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
_API_BASE = "https://analyticsdata.googleapis.com/v1beta"

# A few ready-made presets for list_entities()/convenience -- the connector
# accepts any "dims|metrics" spec, not just these.
_PRESET_ENTITIES = [
    "date|activeUsers,sessions",
    "country|activeUsers",
    "pagePath|screenPageViews",
]


class GA4Connector(Connector):
    name = "ga4"

    def __init__(self, service_account_json_path: str, property_id: str) -> None:
        self._property_id = property_id
        self._credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path, scopes=_SCOPES
        )

    def _headers(self) -> dict:
        if not self._credentials.valid:
            self._credentials.refresh(GoogleAuthRequest())
        return {"Authorization": f"Bearer {self._credentials.token}"}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(
                f"{_API_BASE}/properties/{self._property_id}/metadata", headers=self._headers(), timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return list(_PRESET_ENTITIES)

    def _parse_entity(self, entity: str) -> tuple[list[str], list[str]]:
        try:
            dims_part, metrics_part = entity.split("|")
        except ValueError as exc:
            raise EntityNotFoundError(
                f"Invalid GA4 entity '{entity}' -- expected 'dim1,dim2|metric1,metric2'."
            ) from exc
        dims = [d for d in dims_part.split(",") if d]
        metrics = [m for m in metrics_part.split(",") if m]
        if not dims or not metrics:
            raise EntityNotFoundError(f"GA4 entity '{entity}' needs at least one dimension and one metric.")
        return dims, metrics

    def get_schema(self, entity: str) -> dict:
        dims, metrics = self._parse_entity(entity)
        fields = dims + metrics
        return {
            "fields": fields,
            "field_types": {**{d: "STRING" for d in dims}, **{m: "NUMBER" for m in metrics}},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        dims, metrics = self._parse_entity(entity)
        filters = dict(filters or {})
        start_date = filters.pop("start_date", "30daysAgo")
        end_date = filters.pop("end_date", "today")

        body: dict = {
            "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": m} for m in metrics],
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "limit": str(min(limit, 100000)) if limit else "10000",
        }
        if filters:
            expressions = [
                {"filter": {"fieldName": col, "stringFilter": {"matchType": "EXACT", "value": val}}}
                for col, val in filters.items()
            ]
            body["dimensionFilter"] = expressions[0] if len(expressions) == 1 else {"andGroup": {"expressions": expressions}}

        resp = requests.post(
            f"{_API_BASE}/properties/{self._property_id}:runReport", headers=self._headers(), json=body, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()

        rows = []
        for r in data.get("rows", []):
            row = {}
            for name, dv in zip(dims, r.get("dimensionValues", [])):
                row[name] = dv.get("value")
            for name, mv in zip(metrics, r.get("metricValues", [])):
                row[name] = mv.get("value")
            rows.append(row)

        df = pd.DataFrame(rows, columns=dims + metrics)
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
