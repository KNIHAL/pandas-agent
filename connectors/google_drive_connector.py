"""Google Drive connector -- Drive API v3 (googleapis.com), auth via a
service-account JSON key (google-auth). A service account has no personal
Drive of its own -- the target folder must be explicitly shared with the
service account's email for it to see anything. Entities are Drive file
IDs (names aren't guaranteed unique), scoped to Google Sheets and CSV
files within one folder -- other file types aren't tabular and are out of
scope here.

No live Drive/service-account was available to test against, so this is
verified against a mocked HTTP layer -- see
tests/test_connectors_google_drive.py. Swap in a real key and it should
work unchanged; re-verify against a live folder before relying on it.
"""

from __future__ import annotations

import io

import pandas as pd
import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from .base import Connector
from .errors import EntityNotFoundError

_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
_API_BASE = "https://www.googleapis.com/drive/v3"
_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
_CSV_MIME = "text/csv"


class GoogleDriveConnector(Connector):
    name = "google_drive"

    def __init__(self, service_account_json_path: str, folder_id: str) -> None:
        self._folder_id = folder_id
        self._credentials = service_account.Credentials.from_service_account_file(
            service_account_json_path, scopes=_SCOPES
        )

    def _headers(self) -> dict:
        if not self._credentials.valid:
            self._credentials.refresh(GoogleAuthRequest())
        return {"Authorization": f"Bearer {self._credentials.token}"}

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{_API_BASE}/about", headers=self._headers(), params={"fields": "user"}, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def list_entities(self) -> list[str]:
        params = {
            "q": f"'{self._folder_id}' in parents and trashed = false "
            f"and (mimeType = '{_SHEET_MIME}' or mimeType = '{_CSV_MIME}')",
            "fields": "files(id,name,mimeType)",
        }
        resp = requests.get(f"{_API_BASE}/files", headers=self._headers(), params=params, timeout=10)
        resp.raise_for_status()
        return sorted(f["id"] for f in resp.json().get("files", []))

    def _get_file_meta(self, entity: str) -> dict:
        resp = requests.get(
            f"{_API_BASE}/files/{entity}", headers=self._headers(), params={"fields": "id,name,mimeType"}, timeout=10
        )
        if resp.status_code == 404:
            raise EntityNotFoundError(f"No Drive file '{entity}' (or not shared with the service account).")
        resp.raise_for_status()
        return resp.json()

    def _download_as_df(self, entity: str, meta: dict) -> pd.DataFrame:
        if meta["mimeType"] == _SHEET_MIME:
            resp = requests.get(
                f"{_API_BASE}/files/{entity}/export", headers=self._headers(), params={"mimeType": _CSV_MIME}, timeout=30
            )
        else:
            resp = requests.get(f"{_API_BASE}/files/{entity}", headers=self._headers(), params={"alt": "media"}, timeout=30)
        resp.raise_for_status()
        return pd.read_csv(io.BytesIO(resp.content))

    def get_schema(self, entity: str) -> dict:
        meta = self._get_file_meta(entity)
        df = self._download_as_df(entity, meta)
        return {"fields": list(df.columns), "field_types": {c: str(df[c].dtype) for c in df.columns}}

    def fetch(
        self,
        entity: str,
        *,
        columns: list[str] | None = None,
        limit: int | None = None,
        filters: dict | None = None,
    ) -> pd.DataFrame:
        meta = self._get_file_meta(entity)
        df = self._download_as_df(entity, meta)
        if columns:
            df = df[columns]
        if filters:
            for col, val in filters.items():
                df = df[df[col] == val]
        if limit is not None:
            df = df.head(limit)
        return df.reset_index(drop=True)
