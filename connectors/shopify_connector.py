"""Shopify connector -- Admin REST API, auth via a custom/private app's
Admin API access token (X-Shopify-Access-Token header) generated directly
in a dev store's admin -- no OAuth flow needed, fits a free Partner
account + free dev store same as the other token-based connectors here.

Entities are Shopify's list-able resources (products/orders/customers/
collections/inventory_items); filters pass straight through as Shopify's
own list-endpoint query params. Pagination is cursor-based via the
response's Link header (rel="next"), not the body.

No live Shopify dev store was available to test against, so this is
verified against a mocked HTTP layer mirroring Shopify's documented REST
response shapes -- see tests/test_connectors_shopify.py. Swap in a real
shop + token and it should work unchanged; re-verify against a live dev
store before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_API_VERSION = "2024-01"
_ENTITIES = frozenset({"products", "orders", "customers", "collections", "inventory_items"})


def _parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        segments = part.split(";")
        if len(segments) < 2:
            continue
        url = segments[0].strip().strip("<>")
        rel = segments[1].strip()
        if rel == 'rel="next"':
            return url
    return None


class ShopifyConnector(Connector):
    name = "shopify"

    def __init__(self, shop: str, access_token: str) -> None:
        self._base = f"https://{shop}.myshopify.com/admin/api/{_API_VERSION}"
        self._headers = {"X-Shopify-Access-Token": access_token}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self._base}/shop.json", headers=self._headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(_ENTITIES)

    def _check_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise EntityNotFoundError(f"Unknown Shopify entity '{entity}'. Known: {sorted(_ENTITIES)}")

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        resp = requests.get(f"{self._base}/{entity}.json", headers=self._headers, params={"limit": 1}, timeout=15)
        resp.raise_for_status()
        items = resp.json().get(entity, [])
        if not items:
            return {"fields": [], "field_types": {}}
        sample = items[0]
        return {"fields": list(sample.keys()), "field_types": {k: type(v).__name__ for k, v in sample.items()}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        self._check_entity(entity)
        rows: list[dict] = []
        url = f"{self._base}/{entity}.json"
        params: dict | None = dict(filters or {})
        params["limit"] = min(limit, 250) if limit else 50

        while url:
            resp = requests.get(url, headers=self._headers, params=params, timeout=15)
            resp.raise_for_status()
            rows.extend(resp.json().get(entity, []))
            if limit is not None and len(rows) >= limit:
                break
            url = _parse_next_link(resp.headers.get("Link"))
            params = None  # next-page URL already carries the encoded cursor + params

        df = pd.DataFrame(rows)
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
