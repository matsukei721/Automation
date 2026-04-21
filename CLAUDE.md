# CLAUDE.md

## セキュリティ（最優先）
- `.env` / `config.yaml` の内容は読まない・出力しない
- APIキー・トークン・パスワードは絶対にコードにハードコードしない
- ログにAPIキーや個人情報を出力しない
- 本番環境のデータを直接操作するコードは書かない

## 操作の確認
- 外部URLへのリクエストを伴うコードを実行する前に必ずユーザーに確認を求める
- ファイルの削除・上書きを行う前に必ずユーザーに確認を求める
- GitHub push前に `.env` と `config.yaml` が `.gitignore` に含まれているか確認する

## 言語・環境
- Python 3.11固定（`.python-version` 参照）
- パッケージ管理は `uv` のみ（pip直接実行禁止）
- 依存追加: `uv add <package>`（`uv.lock` を必ずコミットに含める）
- ロガーは `loguru` を使用（`from loguru import logger`）。`setup_logger()` は `main.py` 起動時に1回だけ呼ぶ

## コード品質
- Linter/Formatter は ruff を使用
- コード変更後は必ず `uv run ruff check . && uv run ruff format .` を通す
- 型ヒントを積極的に使用する
- エラー発生時は修正前に原因を説明してからコードを書く
- 推測で複数ファイルを一気に変更しない

## テスト
- テストフレームワークは pytest を使用（未導入時は `uv add --dev pytest` で追加）
- テストファイルは `tests/` に配置し、`test_*.py` の命名規則に従う
- 新機能追加時は基本的なハッピーパステストを必ず作成する
- 実行: `uv run pytest`
- 外部API（Jira・Confluence・Slack・MS Graph）のテストは `unittest.mock` でモック化する

## ディレクトリ構造
- 再利用可能なモジュールは `modules/` 配下に配置する
- エントリーポイントは `main.py` とする
- 既存の `modules/` にある関数を先に確認・再利用する
- 現在の `modules/` 構成: `jira.py` / `confluence.py` / `slack.py` / `excel.py` / `csv_utils.py` / `utils.py` / `logger.py`

## Git
- `main` ブランチへの直接push禁止・機能ブランチを使用する
- コミットメッセージは日本語・英語どちらでも可
- push前に `.gitignore` を必ず確認する

## 完了条件
- コード変更後は ruff を通してから「完了」と報告する
- 未実装部分がある場合は明示する
