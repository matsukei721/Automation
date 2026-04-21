import os
from unittest.mock import MagicMock, patch

import pytest

from modules.slack import SlackClient

_ENV = {"SLACK_BOT_TOKEN": "xoxb-test-token"}


@pytest.fixture
def client():
    with patch.dict(os.environ, _ENV):
        return SlackClient()


def _ok_response(ts: str = "1234567890.000001") -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"ok": True, "ts": ts}
    return mock_resp


def test_post_message(client):
    with patch("modules.slack.requests.post", return_value=_ok_response()):
        result = client.post_message("#general", "Hello")
    assert result["ts"] == "1234567890.000001"


def test_post_message_with_blocks(client):
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "msg"}}]
    with patch("modules.slack.requests.post", return_value=_ok_response()):
        result = client.post_message("#general", "Hello", blocks=blocks)
    assert result["ok"] is True


def test_notify_success(client):
    with patch("modules.slack.requests.post", return_value=_ok_response()):
        result = client.notify_success("#general", "処理完了")
    assert result["ok"] is True


def test_notify_success_with_detail(client):
    with patch("modules.slack.requests.post", return_value=_ok_response()):
        result = client.notify_success("#general", "処理完了", "詳細メッセージ")
    assert result["ok"] is True


def test_notify_error(client):
    with patch("modules.slack.requests.post", return_value=_ok_response("1234567890.000002")):
        result = client.notify_error("#general", "処理失敗", ValueError("test error"))
    assert result["ok"] is True


def test_notify_error_with_traceback(client):
    with patch("modules.slack.requests.post", return_value=_ok_response()):
        result = client.notify_error("#general", "処理失敗", RuntimeError("err"), "Traceback...")
    assert result["ok"] is True
