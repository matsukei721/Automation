"""Microsoft Graph API を使った Excel 操作クライアント。"""

import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from loguru import logger

from modules.utils import load_config

# Excel が日付として扱う代表的な文字列フォーマット（日本語環境に合わせて優先順に列挙）
_DATE_FORMATS = [
    "%Y/%m/%d",
    "%Y-%m-%d",
    "%Y年%m月%d日",
    "%m/%d/%Y",
    "%d/%m/%Y",
]


def _col_letter_to_index(col: str) -> int:
    """列アルファベット（'A', 'G' など）を 0-indexed の整数に変換する。"""
    col = col.upper()
    result = 0
    for ch in col:
        result = result * 26 + (ord(ch) - ord("A") + 1)
    return result - 1


def _parse_date(value: object) -> date | None:
    """セル値を date に変換する。文字列・date・datetime・Excel シリアル値に対応。

    Args:
        value: セルの値

    Returns:
        date オブジェクト、変換失敗時は None
    """
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value

    if isinstance(value, (int, float)):
        # Excel のシリアル日付（1900年1月1日 = 1）を date に変換
        # Excel のバグで 1900/2/29 が存在するため 2 を引く
        try:
            return date(1899, 12, 30) + __import__("datetime").timedelta(days=int(value))
        except (ValueError, OverflowError):
            return None

    if isinstance(value, str):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue

    return None


# ---------------------------------------------------------------------------
# ExcelClient
# ---------------------------------------------------------------------------


class ExcelClient:
    """MS Graph API を経由した Excel ファイル操作クライアント。

    認証は OAuth2 クライアント資格情報フロー（アプリケーション権限）を使用する。

    必要な Azure AD アプリ権限（最小権限の原則に基づき以下を推奨）:
    - Files.Read.All: ファイル・シート読み取りのみが必要な場合
    - Files.ReadWrite.All: ファイル・シート読み取り・書き込みが必要な場合（デフォルト推奨）

    権限の設定方法:
    1. Azure Portal → アプリの登録 → API のアクセス許可
    2. 「Microsoft Graph」を選択
    3. 「アプリケーション権限」から「Files」> 上記権限を追加
    4. 「管理者の同意を与える」をクリック
    """

    def __init__(self) -> None:
        self._client_id = os.environ["MS_GRAPH_CLIENT_ID"]
        self._client_secret = os.environ["MS_GRAPH_CLIENT_SECRET"]
        self._tenant_id = os.environ["MS_GRAPH_TENANT_ID"]

        # トークンキャッシュ
        self._token: str | None = None
        self._token_expires_at: float = 0.0

        # MS Graph エンドポイント（from_config() で config.yaml から上書きされる）
        self._graph_base: str = ""
        self._login_base: str = ""
        self._scope: str = ""

        # from_config() で設定されるデフォルト値
        self.default_file_id: str | None = None
        self.default_drive_id: str | None = None
        self.default_sheet_name: str | None = None
        self.default_start_col: str = "A"
        self.default_end_col: str = "G"

        logger.info("ExcelClient initialized | tenant_id={}", self._tenant_id)

    # ------------------------------------------------------------------
    # コンストラクタ
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config_path: str | Path = "config.yaml") -> "ExcelClient":
        """config.yaml と .env からクライアントを生成する。

        config.yaml の excel セクションから以下を読み込む:
          - file_id   : OneDrive/SharePoint の Drive Item ID
          - drive_id  : Drive ID
          - sheet_name: 対象シート名
          - range.start_col / range.end_col: 入力範囲列

        Args:
            config_path: config.yaml のパス

        Returns:
            ExcelClient インスタンス
        """
        config = load_config(config_path)

        mg = config.get("ms_graph", {})
        if not all([mg.get("graph_base_url"), mg.get("login_base_url"), mg.get("scope")]):
            raise ValueError(
                "config.yaml に ms_graph.graph_base_url / login_base_url / scope が必要です"
            )

        exc = config.get("excel", {})

        instance = cls()
        instance._graph_base = mg["graph_base_url"].rstrip("/")
        instance._login_base = mg["login_base_url"].rstrip("/")
        instance._scope = mg["scope"]
        instance.default_file_id = exc.get("file_id")
        instance.default_drive_id = exc.get("drive_id")
        instance.default_sheet_name = exc.get("sheet_name")

        rng = exc.get("range", {})
        if rng.get("start_col"):
            instance.default_start_col = rng["start_col"].upper()
        if rng.get("end_col"):
            instance.default_end_col = rng["end_col"].upper()

        logger.info(
            "ExcelClient.from_config | file_id={} sheet={}",
            instance.default_file_id,
            instance.default_sheet_name,
        )
        return instance

    # ------------------------------------------------------------------
    # 認証
    # ------------------------------------------------------------------

    def _get_access_token(self) -> str:
        """アクセストークンを取得する（有効期限内はキャッシュを返す）。

        Returns:
            Bearer トークン文字列
        """
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        logger.debug("ExcelClient._get_access_token | fetching new token")
        url = f"{self._login_base}/{self._tenant_id}/oauth2/v2.0/token"
        resp = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": self._scope,
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()

        self._token = body["access_token"]
        self._token_expires_at = time.time() + body.get("expires_in", 3600)
        logger.debug(
            "ExcelClient._get_access_token | token acquired expires_in={}", body.get("expires_in")
        )
        return self._token  # type: ignore[return-value]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_access_token()}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # 内部ヘルパー
    # ------------------------------------------------------------------

    def _workbook_url(self, file_id: str, drive_id: str) -> str:
        """ワークブックの Graph API ベース URL を返す。"""
        return f"{self._graph_base}/drives/{drive_id}/items/{file_id}/workbook"

    def _sheet_url(self, file_id: str, drive_id: str, sheet_name: str) -> str:
        """ワークシートの Graph API ベース URL を返す。"""
        encoded = quote(sheet_name, safe="")
        return f"{self._workbook_url(file_id, drive_id)}/worksheets/{encoded}"

    def _resolve(
        self,
        file_id: str | None,
        drive_id: str | None,
        sheet_name: str | None,
    ) -> tuple[str, str, str]:
        """引数のデフォルト解決。未指定の場合は from_config の値を使用する。

        Raises:
            ValueError: 必須値が解決できない場合
        """
        fid = file_id or self.default_file_id
        did = drive_id or self.default_drive_id
        sname = sheet_name or self.default_sheet_name

        pairs = [("file_id", fid), ("drive_id", did), ("sheet_name", sname)]
        missing = [k for k, v in pairs if not v]
        if missing:
            raise ValueError(
                f"以下の値が未設定です: {missing}。"
                "引数で指定するか from_config() を使用してください。"
            )
        return fid, did, sname  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # シート操作
    # ------------------------------------------------------------------

    def get_sheet(
        self,
        sheet_name: str | None = None,
        file_id: str | None = None,
        drive_id: str | None = None,
    ) -> dict:
        """ワークシートのメタ情報を取得する。

        Args:
            sheet_name: シート名（省略時は config.yaml の値）
            file_id: Drive Item ID（省略時は config.yaml の値）
            drive_id: Drive ID（省略時は config.yaml の値）

        Returns:
            ワークシートのメタ情報辞書
        """
        fid, did, sname = self._resolve(file_id, drive_id, sheet_name)
        logger.info("ExcelClient.get_sheet | sheet={} file_id={}", sname, fid)
        url = self._sheet_url(fid, did, sname)
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        logger.info("ExcelClient.get_sheet | done | sheet={}", sname)
        return resp.json()

    def get_used_range(
        self,
        sheet_name: str | None = None,
        file_id: str | None = None,
        drive_id: str | None = None,
    ) -> dict:
        """シートの使用済み範囲（usedRange）を取得する。

        Args:
            sheet_name: シート名
            file_id: Drive Item ID
            drive_id: Drive ID

        Returns:
            usedRange の JSON レスポンス（values / formulas / address を含む）
        """
        fid, did, sname = self._resolve(file_id, drive_id, sheet_name)
        logger.info("ExcelClient.get_used_range | sheet={}", sname)
        url = f"{self._sheet_url(fid, did, sname)}/usedRange"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        result = resp.json()
        logger.info("ExcelClient.get_used_range | done | address={}", result.get("address"))
        return result

    # ------------------------------------------------------------------
    # 日付検索
    # ------------------------------------------------------------------

    def find_row_by_date(
        self,
        target_date: date | str | None = None,
        date_col: str = "A",
        sheet_name: str | None = None,
        file_id: str | None = None,
        drive_id: str | None = None,
    ) -> int | None:
        """A列（または指定列）から日付を検索し、該当する行番号（1-indexed）を返す。

        Args:
            target_date: 検索する日付。省略時は今日の日付を使用。
            date_col: 日付を検索する列アルファベット（デフォルト: "A"）
            sheet_name: シート名
            file_id: Drive Item ID
            drive_id: Drive ID

        Returns:
            一致した行番号（1-indexed）。見つからない場合は None。
        """
        fid, did, sname = self._resolve(file_id, drive_id, sheet_name)

        # target_date の解決
        if target_date is None:
            td = date.today()
        elif isinstance(target_date, str):
            parsed = _parse_date(target_date)
            if parsed is None:
                raise ValueError(f"日付の解析に失敗しました: {target_date!r}")
            td = parsed
        else:
            td = target_date

        logger.info("ExcelClient.find_row_by_date | sheet={} col={} date={}", sname, date_col, td)

        # 日付列の値を一括取得（最大 2000 行）
        col = date_col.upper()
        address = f"{col}1:{col}2000"
        encoded_addr = quote(f"'{address}'", safe="'")
        url = f"{self._sheet_url(fid, did, sname)}/range(address={encoded_addr})"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        values: list[list] = resp.json().get("values", [])

        for row_idx, row in enumerate(values):
            if not row:
                continue
            cell_date = _parse_date(row[0])
            if cell_date == td:
                row_number = row_idx + 1
                logger.info("ExcelClient.find_row_by_date | found | date={} row={}", td, row_number)
                return row_number

        logger.warning("ExcelClient.find_row_by_date | not found | date={}", td)
        return None

    # ------------------------------------------------------------------
    # データ書き込み
    # ------------------------------------------------------------------

    def write_row(
        self,
        row_number: int,
        data: list[Any],
        start_col: str | None = None,
        end_col: str | None = None,
        sheet_name: str | None = None,
        file_id: str | None = None,
        drive_id: str | None = None,
    ) -> dict:
        """指定した行の start_col〜end_col 範囲にデータを書き込む。

        Args:
            row_number: 書き込み先の行番号（1-indexed）
            data: 書き込むデータのリスト（列数と要素数は一致させること）
            start_col: 書き込み開始列（省略時は config.yaml の値）
            end_col: 書き込み終了列（省略時は config.yaml の値）
            sheet_name: シート名
            file_id: Drive Item ID
            drive_id: Drive ID

        Returns:
            更新後の range オブジェクトの JSON レスポンス

        Raises:
            ValueError: data の要素数が列数と一致しない場合
        """
        fid, did, sname = self._resolve(file_id, drive_id, sheet_name)
        sc = (start_col or self.default_start_col).upper()
        ec = (end_col or self.default_end_col).upper()

        # 列数チェック
        expected_cols = _col_letter_to_index(ec) - _col_letter_to_index(sc) + 1
        if len(data) != expected_cols:
            raise ValueError(
                f"data の要素数 ({len(data)}) が列数 ({expected_cols}: {sc}〜{ec}) と一致しません"
            )

        address = f"{sc}{row_number}:{ec}{row_number}"
        logger.info("ExcelClient.write_row | sheet={} range={}", sname, address)

        encoded_addr = quote(f"'{address}'", safe="'")
        url = f"{self._sheet_url(fid, did, sname)}/range(address={encoded_addr})"

        payload = {"values": [data]}
        resp = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("ExcelClient.write_row | done | range={}", address)
        return resp.json()

    def write_row_by_date(
        self,
        data: list[Any],
        target_date: date | str | None = None,
        date_col: str = "A",
        start_col: str | None = None,
        end_col: str | None = None,
        sheet_name: str | None = None,
        file_id: str | None = None,
        drive_id: str | None = None,
    ) -> dict:
        """日付で行を特定し、その行にデータを書き込む（find_row_by_date + write_row の合成）。

        Args:
            data: 書き込むデータのリスト
            target_date: 検索する日付。省略時は今日の日付（date.today()）を使用。
            date_col: 日付を検索する列アルファベット（デフォルト: "A"）
            start_col: 書き込み開始列（省略時は config.yaml の値）
            end_col: 書き込み終了列（省略時は config.yaml の値）
            sheet_name: シート名
            file_id: Drive Item ID
            drive_id: Drive ID

        Returns:
            更新後の range オブジェクトの JSON レスポンス

        Raises:
            ValueError: 指定した日付に該当する行が見つからない場合
        """
        row_number = self.find_row_by_date(
            target_date=target_date,
            date_col=date_col,
            sheet_name=sheet_name,
            file_id=file_id,
            drive_id=drive_id,
        )

        resolved_date = target_date or date.today()
        if row_number is None:
            raise ValueError(f"日付 {resolved_date} に該当する行が見つかりませんでした")

        return self.write_row(
            row_number=row_number,
            data=data,
            start_col=start_col,
            end_col=end_col,
            sheet_name=sheet_name,
            file_id=file_id,
            drive_id=drive_id,
        )
