"""Stripe connector -- REST API (api.stripe.com/v1), auth via a secret key
(Bearer token). Entities are Stripe's list-able resource types (customers,
charges, ...); filters are passed straight through as Stripe list-endpoint
query params (e.g. {"email": "a@x.com"} for customers) rather than a
generic equality engine, since Stripe's filtering is resource-specific.

No Stripe account was available to test against -- Stripe doesn't
currently allow Indian accounts to self-register -- so this is verified
against a mocked HTTP layer mirroring Stripe's documented response shapes
-- see tests/test_connectors_stripe.py. Swap in a real secret key and it
should work unchanged; re-verify against a live account before relying
on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_BASE_URL = "https://api.stripe.com/v1"

# Stripe has no "list resource types" endpoint -- this is the set of
# list-able resources relevant to a data-analysis use case. Extend as needed.
_ENTITIES = frozenset(
    {
        "customers",
        "charges",
        "invoices",
        "subscriptions",
        "payment_intents",
        "products",
        "prices",
        "refunds",
        "balance_transactions",
    }
)


class StripeConnector(Connector):
    name = "stripe"

    def __init__(self, secret_key: str) -> None:
        self._headers = {"Authorization": f"Bearer {secret_key}"}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{_BASE_URL}/balance", headers=self._headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(_ENTITIES)

    def _check_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise EntityNotFoundError(f"Unknown Stripe entity '{entity}'. Known: {sorted(_ENTITIES)}")

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        resp = requests.get(f"{_BASE_URL}/{entity}", headers=self._headers, params={"limit": 1}, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if not data:
            return {"fields": [], "field_types": {}}
        sample = data[0]
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
        params: dict = dict(filters or {})
        params["limit"] = min(limit, 100) if limit else 100

        rows: list[dict] = []
        while True:
            resp = requests.get(f"{_BASE_URL}/{entity}", headers=self._headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            rows.extend(data.get("data", []))
            if limit is not None and len(rows) >= limit:
                break
            if not data.get("has_more"):
                break
            params["starting_after"] = data["data"][-1]["id"]

        df = pd.DataFrame(rows)
        if limit is not None:
            df = df.head(limit)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
