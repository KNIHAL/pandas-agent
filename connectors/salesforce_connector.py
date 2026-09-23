"""Salesforce connector -- REST API (via SOQL), auth through the OAuth2
username-password flow (a connected app's client_id/client_secret + a
user's username/password+security_token) so no interactive consent
redirect is needed -- fits a backend/service context like the other
connectors here.

Entities are Salesforce SObjects (Account, Contact, Opportunity, ...);
fetch() builds and runs a SOQL query. filters is an exact-match equality
map translated into a SOQL WHERE clause (values are escaped, not bound --
SOQL's REST query endpoint has no parameter-binding API).

No live Salesforce org was available to test against, so this is
verified against a mocked HTTP layer mirroring Salesforce's documented
REST/SOQL response shapes -- see tests/test_connectors_salesforce.py.
Swap in real credentials and it should work unchanged; re-verify against
a live (e.g. free Developer Edition) org before relying on it.
"""

from __future__ import annotations

import pandas as pd
import requests

from .base import Connector
from .errors import ConnectionFailedError, EntityNotFoundError

_API_VERSION = "v59.0"


def _soql_literal(val) -> str:
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("'", "\\'") + "'"


class SalesforceConnector(Connector):
    name = "salesforce"

    def __init__(
        self,
        username: str,
        password: str,
        security_token: str,
        client_id: str,
        client_secret: str,
        login_url: str = "https://login.salesforce.com",
    ) -> None:
        try:
            resp = requests.post(
                f"{login_url}/services/oauth2/token",
                data={
                    "grant_type": "password",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "username": username,
                    "password": f"{password}{security_token}",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            self._instance_url = data["instance_url"]
            self._headers = {"Authorization": f"Bearer {data['access_token']}"}
        except Exception as exc:
            raise ConnectionFailedError(f"Salesforce OAuth2 authentication failed: {exc}") from exc

    def test_connection(self) -> bool:
        try:
            resp = requests.get(
                f"{self._instance_url}/services/data/{_API_VERSION}/", headers=self._headers, timeout=10
            )
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        resp = requests.get(
            f"{self._instance_url}/services/data/{_API_VERSION}/sobjects/", headers=self._headers, timeout=15
        )
        resp.raise_for_status()
        return sorted(s["name"] for s in resp.json().get("sobjects", []) if s.get("queryable"))

    def _describe(self, entity: str) -> dict:
        resp = requests.get(
            f"{self._instance_url}/services/data/{_API_VERSION}/sobjects/{entity}/describe/",
            headers=self._headers,
            timeout=15,
        )
        if resp.status_code == 404:
            raise EntityNotFoundError(f"No Salesforce SObject '{entity}'.")
        resp.raise_for_status()
        return resp.json()

    def get_schema(self, entity: str) -> dict:
        described = self._describe(entity)
        fields = described.get("fields", [])
        return {
            "fields": [f["name"] for f in fields],
            "field_types": {f["name"]: f["type"] for f in fields},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        select_cols = columns or [f["name"] for f in self._describe(entity).get("fields", [])]
        soql = f"SELECT {', '.join(select_cols)} FROM {entity}"
        if filters:
            clauses = [f"{col} = {_soql_literal(val)}" for col, val in filters.items()]
            soql += " WHERE " + " AND ".join(clauses)
        if limit is not None:
            soql += f" LIMIT {int(limit)}"

        records: list[dict] = []
        resp = requests.get(
            f"{self._instance_url}/services/data/{_API_VERSION}/query/",
            headers=self._headers,
            params={"q": soql},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        while not data.get("done", True):
            next_url = data["nextRecordsUrl"]
            resp = requests.get(f"{self._instance_url}{next_url}", headers=self._headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            records.extend(data.get("records", []))

        for r in records:
            r.pop("attributes", None)
        df = pd.DataFrame(records, columns=select_cols)
        return df.reset_index(drop=True)
