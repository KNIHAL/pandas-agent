"""HubSpot connector -- CRM API v3 (api.hubapi.com), auth via a private
app access token (Bearer). Entities are HubSpot's CRM object types
(contacts, companies, deals, tickets, products, line_items); each record's
`properties` map is flattened into columns alongside its `id`. Plain
list (GET) when no filters are given; the /search endpoint (POST) when
filters are given, since HubSpot's plain list endpoint has no generic
equality-filter support.

No live HubSpot account was available to test against, so this is
verified against a mocked HTTP layer mirroring HubSpot's documented REST
response shapes -- see tests/test_connectors_hubspot.py. Swap in a real
private-app token and it should work unchanged; re-verify against a live
(e.g. free CRM + developer test) account before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_BASE_URL = "https://api.hubapi.com/crm/v3"
_ENTITIES = frozenset({"contacts", "companies", "deals", "tickets", "products", "line_items"})


class HubSpotConnector(Connector):
    name = "hubspot"

    def __init__(self, access_token: str) -> None:
        self._headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{_BASE_URL}/objects/contacts", headers=self._headers, params={"limit": 1}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(_ENTITIES)

    def _check_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise EntityNotFoundError(f"Unknown HubSpot entity '{entity}'. Known: {sorted(_ENTITIES)}")

    def _all_properties(self, entity: str) -> list[str]:
        resp = requests.get(f"{_BASE_URL}/properties/{entity}", headers=self._headers, timeout=15)
        resp.raise_for_status()
        return [p["name"] for p in resp.json().get("results", [])]

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        resp = requests.get(f"{_BASE_URL}/properties/{entity}", headers=self._headers, timeout=15)
        resp.raise_for_status()
        props = resp.json().get("results", [])
        return {"fields": [p["name"] for p in props], "field_types": {p["name"]: p.get("type", "string") for p in props}}

    @staticmethod
    def _flatten(item: dict) -> dict:
        return {"id": item.get("id"), **item.get("properties", {})}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        self._check_entity(entity)
        props = columns or self._all_properties(entity)
        page_size = min(limit, 100) if limit else 100
        rows: list[dict] = []

        if filters:
            body: dict = {
                "filterGroups": [
                    {"filters": [{"propertyName": k, "operator": "EQ", "value": v} for k, v in filters.items()]}
                ],
                "properties": props,
                "limit": page_size,
            }
            while True:
                resp = requests.post(f"{_BASE_URL}/objects/{entity}/search", headers=self._headers, json=body, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                rows.extend(self._flatten(item) for item in data.get("results", []))
                after = data.get("paging", {}).get("next", {}).get("after")
                if not after or (limit is not None and len(rows) >= limit):
                    break
                body["after"] = after
        else:
            params: dict = {"properties": ",".join(props), "limit": page_size}
            while True:
                resp = requests.get(f"{_BASE_URL}/objects/{entity}", headers=self._headers, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                rows.extend(self._flatten(item) for item in data.get("results", []))
                after = data.get("paging", {}).get("next", {}).get("after")
                if not after or (limit is not None and len(rows) >= limit):
                    break
                params["after"] = after

        df = pd.DataFrame(rows, columns=["id"] + list(props))
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)
