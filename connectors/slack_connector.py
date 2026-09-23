"""Slack connector -- REST API (slack.com/api), auth via a bot token.
A channel is an entity; fetch() returns its recent messages (ts/user/
text/type columns) via conversations.history.

No live workspace was available to test against, so this is verified
against a mocked HTTP layer mirroring Slack's documented response shapes
-- see tests/test_connectors_slack.py. Swap in a real bot token and it
should work unchanged; re-verify against a live workspace before relying
on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_BASE_URL = "https://slack.com/api"
_MESSAGE_FIELDS = ["ts", "user", "text", "type"]


class SlackConnector(Connector):
    name = "slack"

    def __init__(self, bot_token: str) -> None:
        self._headers = {"Authorization": f"Bearer {bot_token}"}

    def test_connection(self) -> bool:
        try:
            resp = requests.post(f"{_BASE_URL}/auth.test", headers=self._headers, timeout=10)
            return bool(resp.json().get("ok"))
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        names: list[str] = []
        params: dict = {"limit": 200}
        while True:
            resp = requests.get(f"{_BASE_URL}/conversations.list", headers=self._headers, params=params, timeout=10)
            data = resp.json()
            if not data.get("ok"):
                raise EntityNotFoundError(f"Slack API error listing channels: {data.get('error')}")
            names.extend(c["name"] for c in data.get("channels", []))
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
        return sorted(names)

    def _resolve_channel_id(self, entity: str) -> str:
        # Slack channel IDs look like "C0123ABCDEF" -- accept as-is if so shaped.
        if entity[:1] in ("C", "G", "D") and entity[1:].isalnum() and entity.isupper():
            return entity
        params: dict = {"limit": 200}
        while True:
            resp = requests.get(f"{_BASE_URL}/conversations.list", headers=self._headers, params=params, timeout=10)
            data = resp.json()
            if not data.get("ok"):
                raise EntityNotFoundError(f"Slack API error listing channels: {data.get('error')}")
            for c in data.get("channels", []):
                if c["name"] == entity:
                    return c["id"]
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
            params["cursor"] = cursor
        raise EntityNotFoundError(f"No Slack channel named '{entity}'.")

    def get_schema(self, entity: str) -> dict:
        self._resolve_channel_id(entity)  # validates existence
        return {"fields": list(_MESSAGE_FIELDS), "field_types": {f: "string" for f in _MESSAGE_FIELDS}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        channel_id = self._resolve_channel_id(entity)
        rows: list[dict] = []
        params: dict = {"channel": channel_id, "limit": min(limit, 200) if limit else 200}
        while True:
            resp = requests.get(f"{_BASE_URL}/conversations.history", headers=self._headers, params=params, timeout=10)
            data = resp.json()
            if not data.get("ok"):
                raise EntityNotFoundError(f"Slack API error fetching '{entity}': {data.get('error')}")
            for m in data.get("messages", []):
                rows.append({f: m.get(f) for f in _MESSAGE_FIELDS})
            if not data.get("has_more"):
                break
            params["cursor"] = data.get("response_metadata", {}).get("next_cursor")
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
