import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from modules.excel import ExcelClient, _col_letter_to_index, _parse_date

_ENV = {
    "MS_GRAPH_CLIENT_ID": "test-client-id",
    "MS_GRAPH_CLIENT_SECRET": "test-secret",
    "MS_GRAPH_TENANT_ID": "test-tenant",
}


@pytest.fixture
def client():
    with patch.dict(os.environ, _ENV):
        c = ExcelClient()
    c._graph_base = "https://graph.microsoft.com/v1.0"
    c._login_base = "https://login.microsoftonline.com"
    c._scope = "https://graph.microsoft.com/.default"
    c.default_file_id = "test-file-id"
    c.default_drive_id = "test-drive-id"
    c.default_sheet_name = "Sheet1"
    return c


# ------------------------------------------------------------------
# ユーティリティ関数
# ------------------------------------------------------------------


def test_col_letter_to_index_a():
    assert _col_letter_to_index("A") == 0


def test_col_letter_to_index_g():
    assert _col_letter_to_index("G") == 6


def test_col_letter_to_index_z():
    assert _col_letter_to_index("Z") == 25


def test_parse_date_slash_format():
    assert _parse_date("2026/04/22") == date(2026, 4, 22)


def test_parse_date_hyphen_format():
    assert _parse_date("2026-04-22") == date(2026, 4, 22)


def test_parse_date_date_object():
    d = date(2026, 4, 22)
    assert _parse_date(d) == d


def test_parse_date_invalid():
    assert _parse_date("not-a-date") is None


# ------------------------------------------------------------------
# ExcelClient メソッド
# ------------------------------------------------------------------


def test_find_row_by_date(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "values": [["2026/04/20"], ["2026/04/21"], ["2026/04/22"], ["2026/04/23"]]
    }
    with (
        patch.object(client, "_get_access_token", return_value="test-token"),
        patch("modules.excel.requests.get", return_value=mock_resp),
    ):
        result = client.find_row_by_date(date(2026, 4, 22))
    assert result == 3


def test_find_row_by_date_not_found(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"values": [["2026/04/20"], ["2026/04/21"]]}
    with (
        patch.object(client, "_get_access_token", return_value="test-token"),
        patch("modules.excel.requests.get", return_value=mock_resp),
    ):
        result = client.find_row_by_date(date(2026, 4, 22))
    assert result is None


def test_write_row(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"address": "A1:G1"}
    with (
        patch.object(client, "_get_access_token", return_value="test-token"),
        patch("modules.excel.requests.patch", return_value=mock_resp),
    ):
        result = client.write_row(1, ["a", "b", "c", "d", "e", "f", "g"])
    assert result["address"] == "A1:G1"


def test_write_row_by_date(client):
    find_resp = MagicMock()
    find_resp.json.return_value = {"values": [["2026/04/22"]]}
    write_resp = MagicMock()
    write_resp.json.return_value = {"address": "A1:G1"}

    with (
        patch.object(client, "_get_access_token", return_value="test-token"),
        patch("modules.excel.requests.get", return_value=find_resp),
        patch("modules.excel.requests.patch", return_value=write_resp),
    ):
        result = client.write_row_by_date(
            ["a", "b", "c", "d", "e", "f", "g"],
            target_date=date(2026, 4, 22),
        )
    assert result["address"] == "A1:G1"


def test_get_used_range(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"address": "A1:G10", "values": []}
    with (
        patch.object(client, "_get_access_token", return_value="test-token"),
        patch("modules.excel.requests.get", return_value=mock_resp),
    ):
        result = client.get_used_range()
    assert result["address"] == "A1:G10"
