"""BigQuery connector -- official google-cloud-bigquery client, auth via a
service-account JSON key. Works against a project in BigQuery Sandbox mode
(no billing account attached) within its free quota (1TB query/month,
10GB storage) -- no different from a billed project as far as this
connector is concerned.

No live GCP project was available to test against (billing account was
detached, sandbox mode not yet re-enabled), so this is verified against
a mocked bigquery.Client -- see tests/test_connectors_bigquery.py. Swap
in a real service-account key + project/dataset and it should work
unchanged; re-verify against a live project before relying on it.
"""

from __future__ import annotations

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from .base import Connector
from .errors import EntityNotFoundError


class BigQueryConnector(Connector):
    name = "bigquery"

    def __init__(self, service_account_json_path: str, project_id: str, dataset_id: str) -> None:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path,
            scopes=["https://www.googleapis.com/auth/bigquery.readonly"],
        )
        self._client = bigquery.Client(project=project_id, credentials=credentials)
        self._project_id = project_id
        self._dataset_id = dataset_id

    def _table_ref(self, entity: str) -> str:
        return f"`{self._project_id}.{self._dataset_id}.{entity}`"

    def test_connection(self) -> bool:
        try:
            self._client.get_dataset(f"{self._project_id}.{self._dataset_id}")
            return True
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        tables = self._client.list_tables(f"{self._project_id}.{self._dataset_id}")
        return sorted(t.table_id for t in tables)

    def _get_table(self, entity: str):
        try:
            return self._client.get_table(f"{self._project_id}.{self._dataset_id}.{entity}")
        except Exception as exc:
            raise EntityNotFoundError(f"No BigQuery table '{entity}' in '{self._dataset_id}'.") from exc

    def get_schema(self, entity: str) -> dict:
        table = self._get_table(entity)
        return {
            "fields": [f.name for f in table.schema],
            "field_types": {f.name: f.field_type for f in table.schema},
        }

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        self._get_table(entity)  # validates existence
        cols_sql = ", ".join(f"`{c}`" for c in columns) if columns else "*"
        query = f"SELECT {cols_sql} FROM {self._table_ref(entity)}"
        query_params = []
        if filters:
            clauses = []
            for i, (col, val) in enumerate(filters.items()):
                param_name = f"p{i}"
                clauses.append(f"`{col}` = @{param_name}")
                query_params.append(bigquery.ScalarQueryParameter(param_name, _bq_param_type(val), val))
            query += " WHERE " + " AND ".join(clauses)
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        job_config = bigquery.QueryJobConfig(query_parameters=query_params) if query_params else None
        return self._client.query(query, job_config=job_config).to_dataframe()


def _bq_param_type(value) -> str:
    if isinstance(value, bool):
        return "BOOL"
    if isinstance(value, int):
        return "INT64"
    if isinstance(value, float):
        return "FLOAT64"
    return "STRING"
