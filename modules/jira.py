"""Jira API client."""

import os
from pathlib import Path

import requests
import yaml
from loguru import logger
from requests.auth import HTTPBasicAuth


def _load_config(config_path: str | Path) -> dict:
    with Path(config_path).open(encoding="utf-8") as f:
        return yaml.safe_load(f)


class JiraClient:
    """Jira REST API v3 クライアント。

    直接生成:
        client = JiraClient()
        # JIRA_EMAIL_PERSONAL / JIRA_API_TOKEN_PERSONAL を使用

    モード切り替え対応:
        client = JiraClient.from_config()
        # config.yaml の account_mode に応じて PERSONAL / SERVICE を自動選択
    """

    def __init__(self, email: str | None = None, api_token: str | None = None) -> None:
        """
        Args:
            email: Jira ログインメール。省略時は JIRA_EMAIL_PERSONAL を使用。
            api_token: Jira API トークン。省略時は JIRA_API_TOKEN_PERSONAL を使用。
        """
        self.base_url = os.environ["JIRA_BASE_URL"].rstrip("/")
        self.auth = HTTPBasicAuth(
            email or os.environ["JIRA_EMAIL_PERSONAL"],
            api_token or os.environ["JIRA_API_TOKEN_PERSONAL"],
        )
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        self._api = f"{self.base_url}/rest/api/3"
        logger.info("JiraClient initialized | base_url={}", self.base_url)

    @classmethod
    def from_config(cls, config_path: str | Path = "config.yaml") -> "JiraClient":
        """config.yaml の account_mode に応じた認証情報でクライアントを生成する。

        account_mode: personal → JIRA_EMAIL_PERSONAL / JIRA_API_TOKEN_PERSONAL
        account_mode: service  → JIRA_EMAIL_SERVICE  / JIRA_API_TOKEN_SERVICE

        Args:
            config_path: config.yaml のパス

        Returns:
            JiraClient インスタンス
        """
        config = _load_config(config_path)
        mode = config.get("account_mode", "personal").upper()
        logger.info("JiraClient.from_config | account_mode={}", mode.lower())
        return cls(
            email=os.environ[f"JIRA_EMAIL_{mode}"],
            api_token=os.environ[f"JIRA_API_TOKEN_{mode}"],
        )

    # ------------------------------------------------------------------
    # Issue
    # ------------------------------------------------------------------

    def get_issue(self, issue_key: str) -> dict:
        """Issue を取得する。

        Args:
            issue_key: Issue キー（例: "PROJ-123"）

        Returns:
            Issue の JSON レスポンス
        """
        logger.info("JiraClient.get_issue | issue_key={}", issue_key)
        url = f"{self._api}/issue/{issue_key}"
        response = requests.get(url, auth=self.auth, headers=self.headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        status = result.get("fields", {}).get("status", {}).get("name")
        logger.info("JiraClient.get_issue | done | issue_key={} status={}", issue_key, status)
        return result

    def create_issue(
        self, project_key: str, summary: str, description: str = "", issue_type: str = "Task"
    ) -> dict:
        """Issue を作成する。

        Args:
            project_key: プロジェクトキー（例: "PROJ"）
            summary: Issue タイトル
            description: 説明文（ADF形式）
            issue_type: Issue タイプ（Task / Bug / Story など）

        Returns:
            作成された Issue の JSON レスポンス
        """
        logger.info(
            "JiraClient.create_issue | project={} type={} summary={}",
            project_key,
            issue_type,
            summary,
        )
        url = f"{self._api}/issue"
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }
        response = requests.post(
            url, auth=self.auth, headers=self.headers, json=payload, timeout=30
        )
        response.raise_for_status()
        result = response.json()
        logger.info("JiraClient.create_issue | done | key={}", result.get("key"))
        return result

    def update_issue(self, issue_key: str, fields: dict) -> None:
        """Issue を更新する。

        Args:
            issue_key: Issue キー（例: "PROJ-123"）
            fields: 更新するフィールドの辞書
        """
        logger.info(
            "JiraClient.update_issue | issue_key={} fields={}", issue_key, list(fields.keys())
        )
        url = f"{self._api}/issue/{issue_key}"
        payload = {"fields": fields}
        response = requests.put(url, auth=self.auth, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("JiraClient.update_issue | done | issue_key={}", issue_key)

    def search_issues(self, jql: str, max_results: int = 50) -> list[dict]:
        """JQL でIssue を検索する。

        Args:
            jql: JQL クエリ文字列（例: "project = PROJ AND status = 'In Progress'"）
            max_results: 最大取得件数

        Returns:
            Issue のリスト
        """
        logger.info("JiraClient.search_issues | jql={} max_results={}", jql, max_results)
        url = f"{self._api}/search"
        params = {"jql": jql, "maxResults": max_results}
        response = requests.get(
            url, auth=self.auth, headers=self.headers, params=params, timeout=30
        )
        response.raise_for_status()
        issues = response.json().get("issues", [])
        logger.info("JiraClient.search_issues | done | count={}", len(issues))
        return issues

    def add_comment(self, issue_key: str, body: str) -> dict:
        """Issue にコメントを追加する。

        Args:
            issue_key: Issue キー
            body: コメント本文

        Returns:
            作成されたコメントの JSON レスポンス
        """
        logger.info("JiraClient.add_comment | issue_key={}", issue_key)
        url = f"{self._api}/issue/{issue_key}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": body}],
                    }
                ],
            }
        }
        response = requests.post(
            url, auth=self.auth, headers=self.headers, json=payload, timeout=30
        )
        response.raise_for_status()
        result = response.json()
        logger.info("JiraClient.add_comment | done | comment_id={}", result.get("id"))
        return result
