"""Microsoft Teams connector -- Microsoft Graph API (graph.microsoft.com),
auth via the OAuth2 client-credentials flow (app registration + one-time
admin consent, then headless -- no interactive per-user login), fits a
Microsoft 365 Developer Program sandbox tenant same as any other
service-style connector here.

An entity is "<team_id>/<channel_id>"; fetch() returns that channel's
recent messages (id/from/body/created_datetime columns) via
GET /teams/{id}/channels/{id}/messages.

No live tenant was available to test against, so this is verified
against a mocked HTTP layer mirroring Microsoft Graph's documented
response shapes -- see tests/test_connectors_teams.py. Swap in real
tenant/client credentials and it should work unchanged; re-verify
against a live (e.g. free M365 Developer Program) tenant before relying
on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import ConnectionFailedError, EntityNotFoundError

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_MESSAGE_FIELDS = ["id", "from", "body", "created_datetime"]


class TeamsConnector(Connector):
    name = "teams"

    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        try:
            resp = requests.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=15,
            )
            resp.raise_for_status()
            self._headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        except Exception as exc:
            raise ConnectionFailedError(f"Microsoft Graph OAuth2 authentication failed: {exc}") from exc

    def test_connection(self) -> bool:
        try:
            resp = requests.get(
                f"{_GRAPH_BASE}/groups",
                headers=self._headers,
                params={"$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')", "$top": 1},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        entities: list[str] = []
        resp = requests.get(
            f"{_GRAPH_BASE}/groups",
            headers=self._headers,
            params={"$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')", "$select": "id"},
            timeout=15,
        )
        resp.raise_for_status()
        for team in resp.json().get("value", []):
            team_id = team["id"]
            ch_resp = requests.get(f"{_GRAPH_BASE}/teams/{team_id}/channels", headers=self._headers, timeout=15)
            ch_resp.raise_for_status()
            entities.extend(f"{team_id}/{c['id']}" for c in ch_resp.json().get("value", []))
        return sorted(entities)

    def _parse_entity(self, entity: str) -> tuple[str, str]:
        parts = entity.split("/")
        if len(parts) != 2:
            raise EntityNotFoundError(f"Invalid Teams entity '{entity}' -- expected '<team_id>/<channel_id>'.")
        return parts[0], parts[1]

    def get_schema(self, entity: str) -> dict:
        self._parse_entity(entity)  # format check only
        return {"fields": list(_MESSAGE_FIELDS), "field_types": {f: "string" for f in _MESSAGE_FIELDS}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        team_id, channel_id = self._parse_entity(entity)
        rows: list[dict] = []
        url = f"{_GRAPH_BASE}/teams/{team_id}/channels/{channel_id}/messages"
        params: dict | None = {"$top": min(limit, 50) if limit else 50}
        while url:
            resp = requests.get(url, headers=self._headers, params=params, timeout=15)
            if resp.status_code == 404:
                raise EntityNotFoundError(f"No Teams channel '{entity}'.")
            resp.raise_for_status()
            data = resp.json()
            for m in data.get("value", []):
                rows.append(
                    {
                        "id": m.get("id"),
                        "from": (m.get("from") or {}).get("user", {}).get("displayName"),
                        "body": (m.get("body") or {}).get("content"),
                        "created_datetime": m.get("createdDateTime"),
                    }
                )
            url = data.get("@odata.nextLink")
            params = None  # nextLink already includes query params
            if limit is not None and len(rows) >= limit:
                break

        df = pd.DataFrame(rows, columns=_MESSAGE_FIELDS)
        if filters:
            for col, val in filters.items():
                df = df[df[col] == val]
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
