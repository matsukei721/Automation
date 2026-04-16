"""Slack API client."""

import os
from pathlib import Path

import requests


class SlackClient:
    """Slack Web API クライアント。"""

    def __init__(self) -> None:
        self._token = os.environ["SLACK_BOT_TOKEN"]
        self._base_url = "https://slack.com/api"
        self.headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _check_response(self, data: dict) -> dict:
        """Slack API のエラーチェック。

        Raises:
            RuntimeError: API がエラーを返した場合
        """
        if not data.get("ok"):
            raise RuntimeError(f"Slack API error: {data.get('error')}")
        return data

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def post_message(self, channel: str, text: str, blocks: list | None = None) -> dict:
        """チャンネルにメッセージを送信する。

        Args:
            channel: チャンネル ID またはチャンネル名（例: "#general"）
            text: メッセージテキスト（blocks 使用時はフォールバック用）
            blocks: Block Kit のブロックリスト（省略可）

        Returns:
            API レスポンス
        """
        url = f"{self._base_url}/chat.postMessage"
        payload: dict = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return self._check_response(response.json())

    def update_message(self, channel: str, ts: str, text: str, blocks: list | None = None) -> dict:
        """送信済みメッセージを更新する。

        Args:
            channel: チャンネル ID
            ts: メッセージのタイムスタンプ（post_message レスポンスの ts）
            text: 新しいテキスト
            blocks: 新しいブロックリスト（省略可）

        Returns:
            API レスポンス
        """
        url = f"{self._base_url}/chat.update"
        payload: dict = {"channel": channel, "ts": ts, "text": text}
        if blocks:
            payload["blocks"] = blocks
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return self._check_response(response.json())

    def delete_message(self, channel: str, ts: str) -> dict:
        """メッセージを削除する。

        Args:
            channel: チャンネル ID
            ts: メッセージのタイムスタンプ

        Returns:
            API レスポンス
        """
        url = f"{self._base_url}/chat.delete"
        payload = {"channel": channel, "ts": ts}
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return self._check_response(response.json())

    # ------------------------------------------------------------------
    # Channels
    # ------------------------------------------------------------------

    def get_channel_id(self, channel_name: str) -> str | None:
        """チャンネル名からチャンネル ID を取得する。

        Args:
            channel_name: チャンネル名（# なし、例: "general"）

        Returns:
            チャンネル ID、見つからない場合は None
        """
        url = f"{self._base_url}/conversations.list"
        params = {"exclude_archived": True, "limit": 200}
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        data = self._check_response(response.json())
        for channel in data.get("channels", []):
            if channel["name"] == channel_name.lstrip("#"):
                return channel["id"]
        return None

    def list_channels(self, exclude_archived: bool = True) -> list[dict]:
        """チャンネル一覧を取得する。

        Args:
            exclude_archived: アーカイブ済みチャンネルを除外するか

        Returns:
            チャンネルのリスト
        """
        url = f"{self._base_url}/conversations.list"
        params = {"exclude_archived": exclude_archived, "limit": 200}
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return self._check_response(response.json()).get("channels", [])

    # ------------------------------------------------------------------
    # Files
    # ------------------------------------------------------------------

    def upload_file(self, channels: list[str], file_path: str | Path, title: str = "") -> dict:
        """ファイルをアップロードする。

        Args:
            channels: 投稿先チャンネル ID のリスト
            file_path: アップロードするファイルのパス
            title: ファイルタイトル（省略時はファイル名）

        Returns:
            API レスポンス
        """
        url = f"{self._base_url}/files.uploadV2"
        path = Path(file_path)
        upload_headers = {"Authorization": f"Bearer {self._token}"}
        with path.open("rb") as f:
            response = requests.post(
                url,
                headers=upload_headers,
                data={
                    "channels": ",".join(channels),
                    "title": title or path.name,
                    "filename": path.name,
                },
                files={"file": f},
                timeout=60,
            )
        response.raise_for_status()
        return self._check_response(response.json())

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def get_user_info(self, user_id: str) -> dict:
        """ユーザー情報を取得する。

        Args:
            user_id: スラックユーザー ID（例: "U12345678"）

        Returns:
            ユーザー情報の辞書
        """
        url = f"{self._base_url}/users.info"
        params = {"user": user_id}
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        response.raise_for_status()
        return self._check_response(response.json()).get("user", {})
