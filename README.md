# Automation

自動化スクリプト・ツール集

## 環境構築

```bash
# Python 3.11 が必要
uv sync

# .env ファイルに API キーを設定
cp .env.example .env  # 必要に応じて
```

## 実行

```bash
uv run main.py
```

## Lint / Format

```bash
uv run ruff check .
uv run ruff format .
```

## 構成

```
Automation/
├── main.py          # エントリーポイント
├── modules/         # モジュール群
├── .env             # 機密情報（git管理外）
├── pyproject.toml   # プロジェクト設定・依存関係
└── uv.lock          # 依存関係ロックファイル
```
