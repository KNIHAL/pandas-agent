"""QuickBooks Online connector -- REST API (Intuit), auth via an OAuth2
access token + realm_id (company ID). Unlike Salesforce, QuickBooks only
supports the interactive OAuth2 authorization-code flow (no password
grant) -- Kumar completes that once via Intuit's consent screen and
passes the resulting access_token/realm_id in here; this connector
doesn't perform the OAuth dance itself.

Entities are QuickBooks object types (Customer, Invoice, Item, Payment,
Bill, Vendor, Account); fetch() builds and runs a QBO SQL-like query.
filters is an exact-match equality map translated into a WHERE clause.

No live QuickBooks sandbox was available to test against, so this is
verified against a mocked HTTP layer mirroring Intuit's documented REST
response shapes -- see tests/test_connectors_quickbooks.py. Swap in a
real token/realm_id and it should work unchanged; re-verify against a
live sandbox company before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import EntityNotFoundError

_ENTITIES = frozenset({"Customer", "Invoice", "Item", "Payment", "Bill", "Vendor", "Account"})


def _qb_literal(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("'", "\\'") + "'"


class QuickBooksConnector(Connector):
    name = "quickbooks"

    def __init__(self, access_token: str, realm_id: str, environment: str = "sandbox") -> None:
        host = "sandbox-quickbooks.api.intuit.com" if environment == "sandbox" else "quickbooks.api.intuit.com"
        self._base = f"https://{host}/v3/company/{realm_id}"
        self._headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(
                f"{self._base}/query",
                headers=self._headers,
                params={"query": "SELECT * FROM CompanyInfo", "minorversion": 65},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        return sorted(_ENTITIES)

    def _check_entity(self, entity: str) -> None:
        if entity not in _ENTITIES:
            raise EntityNotFoundError(f"Unknown QuickBooks entity '{entity}'. Known: {sorted(_ENTITIES)}")

    def _run_query(self, entity: str, soql: str) -> list[dict]:
        resp = requests.get(
            f"{self._base}/query", headers=self._headers, params={"query": soql, "minorversion": 65}, timeout=15
        )
        resp.raise_for_status()
        return resp.json().get("QueryResponse", {}).get(entity, [])

    def get_schema(self, entity: str) -> dict:
        self._check_entity(entity)
        rows = self._run_query(entity, f"SELECT * FROM {entity} MAXRESULTS 1")
        if not rows:
            return {"fields": [], "field_types": {}}
        sample = rows[0]
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
        cols_sql = ", ".join(columns) if columns else "*"
        soql = f"SELECT {cols_sql} FROM {entity}"
        if filters:
            clauses = [f"{col} = {_qb_literal(val)}" for col, val in filters.items()]
            soql += " WHERE " + " AND ".join(clauses)
        soql += f" MAXRESULTS {int(limit) if limit else 1000}"

        rows = self._run_query(entity, soql)
        df = pd.DataFrame(rows)
        if columns:
            df = df[columns]
        return df.reset_index(drop=True)
