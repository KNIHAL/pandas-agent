"""Tests for connectors.google_drive_connector -- mocked against Drive
API v3's documented REST shapes (no live service account available).
Credential loading + token refresh are also mocked so no real JSON key
file or network call to Google's token endpoint is needed."""

import io
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from connectors.google_drive_connector import GoogleDriveConnector
from connectors.errors import EntityNotFoundError


def _resp(status_code=200, json_data=None, content=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.content = content or b""
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


@pytest.fixture
def connector():
    with patch("connectors.google_drive_connector.service_account.Credentials.from_service_account_file") as mock_creds:
        creds = MagicMock()
        creds.valid = True
        creds.token = "fake-access-token"
        mock_creds.return_value = creds
        yield GoogleDriveConnector("fake-key.json", "folder-123")


@patch("connectors.google_drive_connector.requests.get")
def test_test_connection_true_on_200(mock_get, connector):
    mock_get.return_value = _resp(200)
    assert connector.test_connection() is True


@patch("connectors.google_drive_connector.requests.get")
def test_test_connection_false_on_403(mock_get, connector):
    mock_get.return_value = _resp(403)
    assert connector.test_connection() is False


@patch("connectors.google_drive_connector.requests.get")
def test_list_entities_returns_sorted_file_ids(mock_get, connector):
    mock_get.return_value = _resp(200, {"files": [{"id": "f2", "name": "b"}, {"id": "f1", "name": "a"}]})
    assert connector.list_entities() == ["f1", "f2"]


@patch("connectors.google_drive_connector.requests.get")
def test_get_schema_unknown_file_raises(mock_get, connector):
    mock_get.return_value = _resp(404)
    with pytest.raises(EntityNotFoundError):
        connector.get_schema("nope")


@patch("connectors.google_drive_connector.requests.get")
def test_fetch_csv_file_downloads_via_media(mock_get, connector):
    csv_bytes = b"id,region\n1,us\n2,eu\n"
    mock_get.side_effect = [
        _resp(200, {"id": "f1", "name": "sales.csv", "mimeType": "text/csv"}),
        _resp(200, content=csv_bytes),
    ]
    df = connector.fetch("f1")
    assert len(df) == 2
    assert list(df.columns) == ["id", "region"]
    # media download uses alt=media, not the sheets export endpoint
    assert mock_get.call_args_list[1].kwargs["params"] == {"alt": "media"}


@patch("connectors.google_drive_connector.requests.get")
def test_fetch_google_sheet_uses_export_endpoint(mock_get, connector):
    csv_bytes = b"id,amount\n1,10\n"
    mock_get.side_effect = [
        _resp(200, {"id": "f2", "name": "Budget", "mimeType": "application/vnd.google-apps.spreadsheet"}),
        _resp(200, content=csv_bytes),
    ]
    df = connector.fetch("f2")
    assert len(df) == 1
    assert mock_get.call_args_list[1].kwargs["params"] == {"mimeType": "text/csv"}


@patch("connectors.google_drive_connector.requests.get")
def test_fetch_applies_columns_filters_limit(mock_get, connector):
    csv_bytes = b"id,region\n1,us\n2,eu\n3,us\n"
    mock_get.side_effect = [
        _resp(200, {"id": "f1", "name": "sales.csv", "mimeType": "text/csv"}),
        _resp(200, content=csv_bytes),
    ]
    df = connector.fetch("f1", columns=["region"], filters={"region": "us"}, limit=1)
    assert list(df.columns) == ["region"]
    assert len(df) == 1
