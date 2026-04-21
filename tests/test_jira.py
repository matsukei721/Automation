import os
from unittest.mock import MagicMock, patch

import pytest

from modules.jira import JiraClient

_ENV = {
    "JIRA_BASE_URL": "https://example.atlassian.net",
    "JIRA_EMAIL_PERSONAL": "test@example.com",
    "JIRA_API_TOKEN_PERSONAL": "test-token",
}


@pytest.fixture
def client():
    with patch.dict(os.environ, _ENV):
        return JiraClient()


def test_get_issue(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "key": "PROJ-123",
        "fields": {"status": {"name": "In Progress"}},
    }
    with patch("modules.jira.requests.get", return_value=mock_resp):
        result = client.get_issue("PROJ-123")
    assert result["key"] == "PROJ-123"


def test_create_issue(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"key": "PROJ-124", "id": "10001"}
    with patch("modules.jira.requests.post", return_value=mock_resp):
        result = client.create_issue("PROJ", "Test Issue", "description")
    assert result["key"] == "PROJ-124"


def test_update_issue(client):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    with patch("modules.jira.requests.put", return_value=mock_resp):
        client.update_issue("PROJ-123", {"summary": "Updated"})
    mock_resp.raise_for_status.assert_called_once()


def test_search_issues(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"issues": [{"key": "PROJ-1"}, {"key": "PROJ-2"}]}
    with patch("modules.jira.requests.get", return_value=mock_resp):
        result = client.search_issues("project = PROJ")
    assert len(result) == 2
    assert result[0]["key"] == "PROJ-1"


def test_add_comment(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "10001"}
    with patch("modules.jira.requests.post", return_value=mock_resp):
        result = client.add_comment("PROJ-123", "Test comment")
    assert result["id"] == "10001"
