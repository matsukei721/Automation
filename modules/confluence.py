"""Confluence API client."""

import os
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag
from loguru import logger
from requests.auth import HTTPBasicAuth

from modules.utils import load_config


class ConfluenceClient:
    """Confluence REST API v2 クライアント。

    直接生成:
        client = ConfluenceClient()
        # CONFLUENCE_EMAIL_PERSONAL_WRITE / CONFLUENCE_API_TOKEN_PERSONAL_WRITE を使用

    モード・スコープ切り替え対応:
        client = ConfluenceClient.from_config()
        # config.yaml の account_mode・confluence.scope に応じて自動選択
    """

    def __init__(
        self, email: str | None = None, api_token: str | None = None, scope: str = "write"
    ) -> None:
        """
        Args:
            email: Confluence ログインメール。省略時は CONFLUENCE_EMAIL_PERSONAL_{scope} を使用。
            api_token: Confluence API トークン。省略時は CONFLUENCE_API_TOKEN_PERSONAL_{scope}
                を使用。
            scope: 権限スコープ（'read': 参照のみ / 'write': 読取+書込。
                write トークンは Atlassian 側で read+write 両スコープの付与が必要）
        """
        if scope.lower() not in ("read", "write"):
            raise ValueError(f"scope は 'read' または 'write' である必要があります: {scope!r}")

        self.scope = scope.lower()
        self.base_url = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
        self.auth = HTTPBasicAuth(
            email or os.environ[f"CONFLUENCE_EMAIL_PERSONAL_{scope.upper()}"],
            api_token or os.environ[f"CONFLUENCE_API_TOKEN_PERSONAL_{scope.upper()}"],
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._api = f"{self.base_url}/wiki/api/v2"
        self.default_page_id: str | None = None
        logger.info(
            "ConfluenceClient initialized | base_url={} scope={}", self.base_url, self.scope
        )

    @classmethod
    def from_config(cls, config_path: str | Path = "config.yaml") -> "ConfluenceClient":
        """config.yaml の account_mode と confluence セクションからクライアントを生成する。

        account_mode: personal / service
        confluence.scope: read（参照のみ） / write（読取・作成・更新）
            ※ write トークンは Atlassian 側で read+write 両スコープの付与が必要

        Args:
            config_path: config.yaml のパス

        Returns:
            ConfluenceClient インスタンス
        """
        config = load_config(config_path)
        mode = config.get("account_mode", "personal").upper()
        scope = config.get("confluence", {}).get("scope", "write").upper()

        if mode not in ("PERSONAL", "SERVICE"):
            raise ValueError(
                f"account_mode は 'personal' または 'service' である必要があります: {mode!r}"
            )
        if scope not in ("READ", "WRITE"):
            raise ValueError(
                f"confluence.scope は 'read' または 'write' である必要があります: {scope!r}"
            )

        conf = config.get("confluence", {})
        logger.info(
            "ConfluenceClient.from_config | account_mode={} scope={}", mode.lower(), scope.lower()
        )

        instance = cls(
            email=os.environ[f"CONFLUENCE_EMAIL_{mode}_{scope}"],
            api_token=os.environ[f"CONFLUENCE_API_TOKEN_{mode}_{scope}"],
            scope=scope.lower(),
        )
        instance.default_page_id = str(conf["page_id"]) if conf.get("page_id") else None
        return instance

    def _check_write_scope(self) -> None:
        """WRITE スコープ要件をチェック。READ では実行不可な操作を防止する。"""
        if self.scope == "read":
            raise PermissionError(
                f"この操作は WRITE スコープが必要です。現在のスコープ: {self.scope}"
            )

    # ------------------------------------------------------------------
    # Pages
    # ------------------------------------------------------------------

    def get_page(self, page_id: str) -> dict:
        """ページを取得する（ストレージ形式の本文を含む）。

        Args:
            page_id: ページ ID

        Returns:
            ページの JSON レスポンス（body.storage.value にHTML本文）
        """
        logger.info("ConfluenceClient.get_page | page_id={}", page_id)
        url = f"{self._api}/pages/{page_id}"
        params = {"body-format": "storage"}
        response = requests.get(
            url, auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        response.raise_for_status()
        result = response.json()
        logger.info("ConfluenceClient.get_page | done | title={}", result.get("title"))
        return result

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
        self._check_write_scope()
        logger.info("ConfluenceClient.create_page | space_id={} title={}", space_id, title)
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
        result = response.json()
        logger.info("ConfluenceClient.create_page | done | page_id={}", result.get("id"))
        return result

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
        self._check_write_scope()
        logger.info(
            "ConfluenceClient.update_page | page_id={} title={} version={}->{}",
            page_id,
            title,
            version,
            version + 1,
        )
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
        logger.info("ConfluenceClient.update_page | done | page_id={}", page_id)
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
        logger.info("ConfluenceClient.search_pages | query={} space_key={}", query, space_key)
        url = f"{self._api}/search"
        cql = f'type=page AND title~"{query}"'
        if space_key:
            cql += f' AND space.key="{space_key}"'
        params = {"query": cql, "limit": limit}
        response = requests.get(
            url, auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        logger.info("ConfluenceClient.search_pages | done | count={}", len(results))
        return results

    def get_page_children(self, page_id: str) -> list[dict]:
        """子ページの一覧を取得する。

        Args:
            page_id: 親ページ ID

        Returns:
            子ページのリスト
        """
        logger.info("ConfluenceClient.get_page_children | page_id={}", page_id)
        url = f"{self._api}/pages/{page_id}/children"
        response = requests.get(url, auth=self.auth, headers=self.headers, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])
        logger.info("ConfluenceClient.get_page_children | done | count={}", len(results))
        return results

    # ------------------------------------------------------------------
    # Table utilities
    # ------------------------------------------------------------------

    def get_first_table(self, page_id: str | None = None) -> Tag:
        """ページ内の最初のテーブルを BeautifulSoup の Tag として返す。

        Args:
            page_id: ページ ID（省略時は from_config で設定された default_page_id を使用）

        Returns:
            最初の <table> タグ

        Raises:
            ValueError: page_id が未指定かつ default_page_id も未設定の場合
            ValueError: ページにテーブルが存在しない場合
        """
        pid = self._resolve_page_id(page_id)
        logger.info("ConfluenceClient.get_first_table | page_id={}", pid)
        page = self.get_page(pid)
        body_html = page["body"]["storage"]["value"]
        soup = BeautifulSoup(body_html, "html.parser")
        table = soup.find("table")
        if not table or not isinstance(table, Tag):
            raise ValueError(f"ページ {pid} にテーブルが見つかりません")
        logger.info("ConfluenceClient.get_first_table | done | page_id={}", pid)
        return table

    def insert_row_below_header(
        self,
        row_data: list[str],
        page_id: str | None = None,
    ) -> dict:
        """ページ内の最初のテーブルのヘッダー行直下に新しい行を追加する。

        1. ページを取得してストレージ形式の HTML を解析
        2. 最初の <table> を特定
        3. ヘッダー行（<th> を含む最初の <tr>）の直後に新しい <tr> を挿入
        4. 変更した HTML でページを更新

        Args:
            row_data: 追加する行のセルデータのリスト（列順）
            page_id: ページ ID（省略時は from_config で設定された default_page_id を使用）

        Returns:
            更新後のページの JSON レスポンス

        Raises:
            ValueError: page_id 未指定 / テーブル未検出 / ヘッダー行未検出
        """
        self._check_write_scope()
        pid = self._resolve_page_id(page_id)
        logger.info(
            "ConfluenceClient.insert_row_below_header | page_id={} cols={}",
            pid,
            len(row_data),
        )

        # ページ取得
        page = self.get_page(pid)
        version: int = page["version"]["number"]
        title: str = page["title"]
        body_html: str = page["body"]["storage"]["value"]

        # HTML パース
        soup = BeautifulSoup(body_html, "html.parser")
        table = soup.find("table")
        if not table or not isinstance(table, Tag):
            raise ValueError(f"ページ {pid} にテーブルが見つかりません")

        # ヘッダー行を特定（<th> を含む最初の <tr>）
        header_row = table.find("tr", recursive=True)
        if not header_row or not isinstance(header_row, Tag):
            raise ValueError("テーブルに行が見つかりません")

        # 新しい行を生成
        new_row = soup.new_tag("tr")
        for cell in row_data:
            td = soup.new_tag("td", attrs={"class": "confluenceTd"})
            p = soup.new_tag("p")
            p.string = str(cell)
            td.append(p)
            new_row.append(td)

        # ヘッダー行の直後に挿入
        header_row.insert_after(new_row)

        # ページ更新
        updated_body = str(soup)
        result = self.update_page(pid, title, updated_body, version)
        logger.info("ConfluenceClient.insert_row_below_header | done | page_id={}", pid)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_page_id(self, page_id: str | None) -> str:
        """page_id を解決する。引数が None の場合は default_page_id を返す。

        Raises:
            ValueError: 両方とも未設定の場合
        """
        pid = page_id or self.default_page_id
        if not pid:
            raise ValueError(
                "page_id を指定するか、from_config() で config.yaml から読み込んでください"
            )
        return pid
