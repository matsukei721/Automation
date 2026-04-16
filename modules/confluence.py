"""Confluence API client."""

import os

import requests
from requests.auth import HTTPBasicAuth


class ConfluenceClient:
    """Confluence REST API v2 クライアント。"""

    def __init__(self) -> None:
        self.base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
        self.auth = HTTPBasicAuth(
            os.environ["CONFLUENCE_EMAIL"],
            os.environ["CONFLUENCE_API_TOKEN"],
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._api = f"{self.base_url}/wiki/api/v2"

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> dict:
        """ページを取得する。

        Args:
            page_id: ページ ID

        Returns:
            ページの JSON レスポンス
        """
        url = f"{self._api}/pages/{page_id}"
        params = {"body-format": "storage"}
        response = requests.get(
            url, auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def create_page(
        self, space_id: str, title: str, body: str, parent_id: str | None = None
    ) -> dict:
        """ページを作成する。

        Args:
            space_id: スペース ID
            title: ページタイトル
            body: ページ本文（ストレージ形式の HTML）
            parent_id: 親ページ ID（省略時はスペースのルート）

        Returns:
            作成されたページの JSON レスポンス
        """
        url = f"{self._api}/pages"
        payload: dict = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body,
            },
        }
        if parent_id:
            payload["parentId"] = parent_id

        response = requests.post(
            url, auth=self.auth, headers=self.headers, json=payload, timeout=30
        )
        response.raise_for_status()
        return response.json()

    def update_page(self, page_id: str, title: str, body: str, version: int) -> dict:
        """ページを更新する。

        Args:
            page_id: ページ ID
            title: 新しいタイトル
            body: 新しい本文（ストレージ形式の HTML）
            version: 現在のバージョン番号（+1 して送信）

        Returns:
            更新されたページの JSON レスポンス
        """
        url = f"{self._api}/pages/{page_id}"
        payload = {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": body,
            },
            "version": {"number": version + 1},
        }
        response = requests.put(url, auth=self.auth, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def search_pages(self, query: str, space_key: str | None = None, limit: int = 25) -> list[dict]:
        """CQL でページを検索する。

        Args:
            query: 検索キーワード（タイトル部分一致）
            space_key: スペースキーで絞り込み（省略時は全スペース）
            limit: 最大取得件数

        Returns:
            ページのリスト
        """
        url = f"{self.base_url}/wiki/rest/api/content/search"
        cql = f'type=page AND title~"{query}"'
        if space_key:
            cql += f' AND space.key="{space_key}"'
        params = {"cql": cql, "limit": limit}
        response = requests.get(
            url, auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        response.raise_for_status()
        return response.json().get("results", [])

    def get_page_children(self, page_id: str) -> list[dict]:
        """子ページの一覧を取得する。

        Args:
            page_id: 親ページ ID

        Returns:
            子ページのリスト
        """
        url = f"{self._api}/pages/{page_id}/children"
        response = requests.get(url, auth=self.auth, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json().get("results", [])
