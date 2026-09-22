"""Notion connector -- REST API (api.notion.com), auth via an integration
token. A Notion "database" (in the structured-table sense) is an entity;
its pages are rows, its properties are columns. Entities are addressed by
database ID (title isn't guaranteed unique).

No live account was available to test against (needs a Notion workspace +
integration token), so this is verified against a mocked HTTP layer that
mirrors Notion's documented request/response shapes -- see
tests/test_connectors_notion.py. Swap in a real token and it should work
unchanged; re-verify against a live workspace before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_NOTION_VERSION = "2022-06-28"
_BASE_URL = "https://api.notion.com/v1"


def _extract_value(prop: dict):
    ptype = prop.get("type")
    value = prop.get(ptype)
    if ptype in ("title", "rich_text"):
        return "".join(t.get("plain_text", "") for t in value) if value else None
    if ptype in ("number", "url", "email", "phone_number", "checkbox", "created_time", "last_edited_time"):
        return value
    if ptype in ("select", "status"):
        return value["name"] if value else None
    if ptype == "multi_select":
        return [v["name"] for v in value] if value else []
    if ptype == "date":
        return value.get("start") if value else None
    if ptype == "people":
        return [p.get("name") for p in value] if value else []
    if ptype == "relation":
        return [r["id"] for r in value] if value else []
    if ptype in ("formula", "rollup"):
        inner = value or {}
        return inner.get(inner.get("type"))
    return value


def _build_filter(props_meta: dict, filters: dict) -> dict:
    conditions = []
    for col, val in filters.items():
        ptype = props_meta.get(col, {}).get("type", "rich_text")
        if ptype == "title":
            cond = {"property": col, "title": {"equals": val}}
        elif ptype == "number":
            cond = {"property": col, "number": {"equals": val}}
        elif ptype in ("select", "status"):
            cond = {"property": col, ptype: {"equals": val}}
        elif ptype == "checkbox":
            cond = {"property": col, "checkbox": {"equals": val}}
        elif ptype == "date":
            cond = {"property": col, "date": {"equals": val}}
        else:
            cond = {"property": col, "rich_text": {"equals": val}}
        conditions.append(cond)
    return conditions[0] if len(conditions) == 1 else {"and": conditions}


class NotionConnector(Connector):
    name = "notion"

    def __init__(self, api_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{_BASE_URL}/users/me", headers=self._headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        entities: list[str] = []
        body: dict = {"filter": {"property": "object", "value": "database"}, "page_size": 100}
        while True:
            resp = requests.post(f"{_BASE_URL}/search", headers=self._headers, json=body, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            entities.extend(r["id"] for r in data.get("results", []))
            if not data.get("has_more"):
                break
            body["start_cursor"] = data["next_cursor"]
        return sorted(entities)

    def _get_database(self, entity: str) -> dict:
        resp = requests.get(f"{_BASE_URL}/databases/{entity}", headers=self._headers, timeout=10)
        if resp.status_code == 404:
            raise EntityNotFoundError(f"No Notion database '{entity}'.")
        resp.raise_for_status()
        return resp.json()

    def get_schema(self, entity: str) -> dict:
        props = self._get_database(entity).get("properties", {})
        return {
            "fields": list(props.keys()),
            "field_types": {name: meta.get("type", "unknown") for name, meta in props.items()},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ):
        props_meta = self._get_database(entity).get("properties", {})
        body: dict = {"page_size": min(limit, 100) if limit else 100}
        if filters:
            body["filter"] = _build_filter(props_meta, filters)

        rows: list[dict] = []
        while True:
            resp = requests.post(f"{_BASE_URL}/databases/{entity}/query", headers=self._headers, json=body, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            for page in data.get("results", []):
                rows.append({name: _extract_value(prop) for name, prop in page.get("properties", {}).items()})
                if limit is not None and len(rows) >= limit:
                    break
            if limit is not None and len(rows) >= limit:
                break
            if not data.get("has_more"):
                break
            body["start_cursor"] = data["next_cursor"]

        df = pd.DataFrame(rows)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
