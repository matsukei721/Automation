# Automation

Jira / Confluence / Slack / Excel（MS Graph）を組み合わせた業務自動化ツール集。

---

## 目次

- [環境構築](#環境構築)
- [設定ファイル](#設定ファイル)
- [アカウントモードの切り替え](#アカウントモードの切り替え)
- [モジュール使い方](#モジュール使い方)
- [ログ](#ログ)
- [開発コマンド](#開発コマンド)
- [ディレクトリ構成](#ディレクトリ構成)

---

## 環境構築

**必要なもの**
- Python 3.11
- [uv](https://docs.astral.sh/uv/)

> **このリポジトリを初めて使う場合**
> `.env` と `config.yaml` はセキュリティ上の理由から git 管理対象外のため、リポジトリには含まれていません。
> 以下の手順に従って **自分の環境で作成する必要があります**。

```bash
# 1. 依存パッケージのインストール
uv sync

# 2. 設定ファイルをサンプルからコピーして作成
cp config.yaml.example config.yaml

# 3. .env を作成（.env.example が存在する場合）
cp .env.example .env

# 4. config.yaml と .env をそれぞれ自分の環境の値に書き換える
#    （下記「設定ファイル」参照）
```

---

## 設定ファイル

### `.env`（機密情報・git管理外）

> **自分の環境で作成が必要なファイルです。**
> `.env.example` をコピーして作成し、各サービスの値を設定してください。
> APIキーやトークン等の機密情報が含まれるため、絶対にコミット・pushしないでください。

```bash
cp .env.example .env
```

設定が必要な値は以下の通りです。

#### Jira / Confluence

| 変数名 | 説明 | 取得元 |
|---|---|---|
| `JIRA_BASE_URL` | Jira のベース URL | 社内の Atlassian ドメイン |
| `JIRA_EMAIL_PERSONAL` | 個人アカウントのメールアドレス | 自分の Atlassian ログインメール |
| `JIRA_API_TOKEN_PERSONAL` | 個人アカウントの API トークン | [Atlassian アカウント設定](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_EMAIL_SERVICE` | サービスアカウントのメールアドレス | 管理者に確認 |
| `JIRA_API_TOKEN_SERVICE` | サービスアカウントの API トークン | 管理者に確認 |
| `CONFLUENCE_BASE_URL` | Confluence のベース URL | 社内の Atlassian ドメイン（Jira と同じことが多い） |
| `CONFLUENCE_EMAIL_*` / `CONFLUENCE_API_TOKEN_*` | Jira と同様 | Jira と同じ Atlassian アカウント |

#### Slack

| 変数名 | 説明 | 取得元 |
|---|---|---|
| `SLACK_BOT_TOKEN` | Bot トークン（`xoxb-` から始まる） | [Slack API](https://api.slack.com/apps) → アプリ選択 → OAuth & Permissions |

必要なスコープ: `chat:write` / `channels:read` / `files:write` / `users:read`

#### Microsoft Graph API（Excel）

| 変数名 | 説明 | 取得元 |
|---|---|---|
| `MS_GRAPH_CLIENT_ID` | アプリケーション（クライアント）ID | [Azure Portal](https://portal.azure.com) → アプリの登録 |
| `MS_GRAPH_CLIENT_SECRET` | クライアントシークレット | Azure Portal → 証明書とシークレット |
| `MS_GRAPH_TENANT_ID` | ディレクトリ（テナント）ID | Azure Portal → アプリの登録 |

必要な API 権限: `Files.ReadWrite.All`（アプリケーション権限）

### `config.yaml`（環境固有の設定・git管理外）

> **自分の環境で作成が必要なファイルです。**
> リポジトリには含まれていないため、`config.yaml.example` をコピーして作成してください。
> 会社固有の情報（ドメイン・各種ID）が含まれるため、絶対にコミット・pushしないでください。

```yaml
# personal: 個人アカウント / service: 会社共有サービスアカウント
account_mode: personal

slack:
  notify_channel: "#general"   # 実行結果の通知先チャンネル

confluence:
  base_url: https://your-domain.atlassian.net
  page_id: "123456789"         # 操作対象のページID

ms_graph:
  graph_base_url: https://graph.microsoft.com/v1.0
  login_base_url: https://login.microsoftonline.com
  scope: https://graph.microsoft.com/.default

excel:
  file_id: "your-file-item-id"  # OneDrive/SharePoint の Drive Item ID
  drive_id: "your-drive-id"     # Drive ID
  sheet_name: "Sheet1"
  range:
    start_col: "A"
    end_col: "G"
```

---

## アカウントモードの切り替え

`config.yaml` の **1行だけ** 変更することで認証アカウントを切り替えられる。

```yaml
# 個人アカウントで動かす場合
account_mode: personal

# 会社共有のサービスアカウントに切り替える場合
account_mode: service
```

| モード | 使用される環境変数 |
|---|---|
| `personal` | `JIRA_EMAIL_PERSONAL` / `JIRA_API_TOKEN_PERSONAL` など |
| `service` | `JIRA_EMAIL_SERVICE` / `JIRA_API_TOKEN_SERVICE` など |

Slack・Excel（MS Graph）はアプリ権限のため、モード切り替えの影響を受けない。

---

## モジュール使い方

すべてのクライアントは `from_config()` で生成するのが基本。

```python
from dotenv import load_dotenv
load_dotenv()

from modules import setup_logger
from modules import JiraClient, ConfluenceClient, SlackClient, ExcelClient

setup_logger()  # ログ初期化（main.py で一度だけ呼ぶ）
```

### JiraClient

```python
jira = JiraClient.from_config()

# Issue取得
issue = jira.get_issue("PROJ-123")

# Issue作成
new_issue = jira.create_issue(
    project_key="PROJ",
    summary="タスクのタイトル",
    description="詳細説明",
    issue_type="Task",   # Task / Bug / Story など
)

# JQLで検索
issues = jira.search_issues("project = PROJ AND status = 'In Progress'")

# フィールド更新
jira.update_issue("PROJ-123", {"status": {"name": "Done"}})

# コメント追加
jira.add_comment("PROJ-123", "対応完了しました。")
```

### ConfluenceClient

```python
confluence = ConfluenceClient.from_config()
# config.yaml の confluence.page_id が default_page_id として自動設定される

# ページ取得
page = confluence.get_page("123456789")

# ページ作成
new_page = confluence.create_page(
    space_id="SPACE_ID",
    title="ページタイトル",
    body="<p>本文</p>",
    parent_id="987654321",   # 省略可
)

# ページ更新
confluence.update_page("123456789", "新しいタイトル", "<p>新しい本文</p>", version=3)

# テーブルのヘッダー行直下に行を挿入
# page_id 省略時は config.yaml の confluence.page_id を使用
confluence.insert_row_below_header(["2026/04/16", "タスク名", "完了", "田中"])
```

### SlackClient

```python
slack = SlackClient()

# メッセージ送信
slack.post_message("#general", "こんにちは")

# 成功通知（緑チェック付き）
slack.notify_success("#general", "日次処理 完了", "全10件処理しました")

# エラー通知（スタックトレース付き）
import traceback
try:
    ...
except Exception as e:
    slack.notify_error("#general", "日次処理 失敗", e, traceback.format_exc())
```

### ExcelClient

```python
excel = ExcelClient.from_config()

# シート情報取得
sheet = excel.get_sheet()

# 今日の日付の行にデータを書き込む（A列で日付を検索）
excel.write_row_by_date(
    data=["2026/04/16", "タスク", "完了", "田中", "3h", "備考", ""],
    # target_date 省略時は date.today() を使用
)

# 日付を明示する場合
excel.write_row_by_date(
    data=["2026/04/15", "タスク", "完了", "田中", "2h", "", ""],
    target_date="2026/04/15",
)

# 行番号を直接指定して書き込む
excel.write_row(row_number=5, data=["A", "B", "C", "D", "E", "F", "G"])
```

### utils（日付ユーティリティ）

```python
from modules.utils import today, format_date, date_range
from datetime import date

# 今日の日付
d = today()                             # date(2026, 4, 16)

# フォーマット変換
format_date(d)                          # "2026/04/16"
format_date(d, "%Y-%m-%d")             # "2026-04-16"
format_date(d, "%Y年%m月%d日")         # "2026年04月16日"

# 日付範囲の生成
for d in date_range(date(2026, 4, 1), date(2026, 4, 5)):
    print(d)
# 2026-04-01, 2026-04-02, ... , 2026-04-05
```

---

## ログ

実行ログは `logs/` ディレクトリに日付ごとのファイルで保存される。

```
logs/
└── 2026-04-16.log   # その日の実行ログ（自動生成・30日保持）
```

ログフォーマット:
```
2026-04-16 10:23:45.123 | INFO     | jira:get_issue:81 | JiraClient.get_issue | issue_key=PROJ-123
2026-04-16 10:23:45.456 | INFO     | jira:get_issue:87 | JiraClient.get_issue | done | issue_key=PROJ-123 status=In Progress
```

ログレベルを変更する場合:
```python
setup_logger(level="DEBUG")   # DEBUG / INFO / WARNING / ERROR
```

---

## 開発コマンド

```bash
# 実行
uv run main.py

# Lintチェック
uv run ruff check .

# 自動フォーマット
uv run ruff format .

# パッケージ追加
uv add <package-name>
```

---

## ディレクトリ構成

```
Automation/
├── main.py               # エントリーポイント（try/except + Slack通知）
├── config.yaml           # 環境固有の設定（git管理外・要自己作成）
├── config.yaml.example   # config.yaml のサンプル（git管理対象）
├── .env                  # 機密情報（APIキー等・git管理外・要自己作成）
├── pyproject.toml        # プロジェクト設定・依存関係
├── uv.lock               # 依存関係ロックファイル
├── .python-version       # Python バージョン固定（3.11）
├── modules/
│   ├── __init__.py       # 各クライアントのエクスポート
│   ├── jira.py           # Jira REST API v3 クライアント
│   ├── confluence.py     # Confluence REST API v2 クライアント
│   ├── slack.py          # Slack Web API クライアント（通知機能含む）
│   ├── excel.py          # MS Graph API 経由の Excel 操作クライアント
│   ├── logger.py         # ログ設定（loguru・日付ローテーション）
│   └── utils.py          # 日付ユーティリティ関数
└── logs/
    └── YYYY-MM-DD.log    # 実行ログ（自動生成・git管理外）
```
