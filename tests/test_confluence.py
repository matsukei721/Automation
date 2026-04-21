import os
from unittest.mock import MagicMock, patch

import pytest

from modules.confluence import ConfluenceClient

_ENV = {
    "CONFLUENCE_BASE_URL": "https://example.atlassian.net",
    "CONFLUENCE_EMAIL_PERSONAL": "test@example.com",
    "CONFLUENCE_API_TOKEN_PERSONAL": "test-token",
}

_PAGE_HTML = """
<table>
  <tr><th>Name</th><th>Value</th></tr>
  <tr><td>existing</td><td>row</td></tr>
</table>
"""


@pytest.fixture
def client():
    with patch.dict(os.environ, _ENV):
        c = ConfluenceClient()
    c.default_page_id = "123"
    return c


def test_get_page(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "id": "123",
        "title": "Test Page",
        "body": {"storage": {"value": "<p>content</p>"}},
    }
    with patch("modules.confluence.requests.get", return_value=mock_resp):
        result = client.get_page("123")
    assert result["title"] == "Test Page"


def test_create_page(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "456", "title": "New Page"}
    with patch("modules.confluence.requests.post", return_value=mock_resp):
        result = client.create_page("SPACE1", "New Page", "<p>body</p>")
    assert result["id"] == "456"


def test_update_page(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "123", "title": "Updated"}
    with patch("modules.confluence.requests.put", return_value=mock_resp):
        result = client.update_page("123", "Updated", "<p>new body</p>", 1)
    assert result["title"] == "Updated"


def test_search_pages(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"id": "1"}, {"id": "2"}]}
    with patch("modules.confluence.requests.get", return_value=mock_resp):
        result = client.search_pages("keyword")
    assert len(result) == 2


def test_insert_row_below_header(client):
    get_resp = MagicMock()
    get_resp.json.return_value = {
        "id": "123",
        "title": "Test Page",
        "version": {"number": 1},
        "body": {"storage": {"value": _PAGE_HTML}},
    }
    put_resp = MagicMock()
    put_resp.json.return_value = {"id": "123", "title": "Test Page"}

    with (
        patch("modules.confluence.requests.get", return_value=get_resp),
        patch("modules.confluence.requests.put", return_value=put_resp),
    ):
        result = client.insert_row_below_header(["New", "Row"])
    assert result["id"] == "123"
