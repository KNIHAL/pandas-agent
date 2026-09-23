"""WooCommerce connector -- REST API v3 on the store's own WordPress site
(<site>/wp-json/wc/v3/<resource>), auth via consumer key/secret (HTTP
Basic auth, requires HTTPS). Entities are WooCommerce's list-able
resources; filters are passed straight through as WooCommerce's own
list-endpoint query params (e.g. {"status": "completed"} for orders).

No live WooCommerce store was available to test against, so this is
verified against a mocked HTTP layer mirroring WooCommerce's documented
REST response shapes -- see tests/test_connectors_woocommerce.py. Swap
in a real site + keys and it should work unchanged; re-verify against a
live store before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_ENTITIES = frozenset({"products", "orders", "customers", "coupons", "refunds"})


class WooCommerceConnector(Connector):
    name = "woocommerce"

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str) -> None:
        self._base = f"{site_url.rstrip('/')}/wp-json/wc/v3"
        self._auth = (consumer_key, consumer_secret)

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self._base}/products", auth=self._auth, params={"per_page": 1}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(_ENTITIES)

    def _check_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise EntityNotFoundError(f"Unknown WooCommerce entity '{entity}'. Known: {sorted(_ENTITIES)}")

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        resp = requests.get(f"{self._base}/{entity}", auth=self._auth, params={"per_page": 1}, timeout=10)
        resp.raise_for_status()
        items = resp.json()
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
        per_page = min(limit, 100) if limit else 100
        params: dict = dict(filters or {})
        params["per_page"] = per_page
        params["page"] = 1

        rows: list[dict] = []
        while True:
            resp = requests.get(f"{self._base}/{entity}", auth=self._auth, params=params, timeout=10)
            resp.raise_for_status()
            page_items = resp.json()
            rows.extend(page_items)
            if limit is not None and len(rows) >= limit:
                break
            if len(page_items) < per_page:
                break
            params["page"] += 1

        df = pd.DataFrame(rows)
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
