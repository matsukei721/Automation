"""ログ設定モジュール。

使い方:
    main.py の起動時に setup_logger() を1回呼ぶ。
    各モジュールは `from loguru import logger` だけで使用できる。
"""

import sys
from pathlib import Path

from loguru import logger

__all__ = ["logger", "setup_logger"]

_LOG_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {module}:{function}:{line} | {message}"


def setup_logger(log_dir: str = "logs", level: str = "INFO") -> None:
    """ロガーを初期化する。

    - コンソール（stderr）に色付きで出力
    - logs/YYYY-MM-DD.log に日付ローテーションで保存（30日保持）

    Args:
        log_dir: ログファイルの出力ディレクトリ（デフォルト: "logs"）
        level: 最低ログレベル（デフォルト: "INFO"）
    """
    Path(log_dir).mkdir(exist_ok=True)

    # デフォルトのコンソールハンドラを上書き（フォーマット統一）
    logger.remove()
    logger.add(sys.stderr, level=level, format=_LOG_FORMAT, colorize=True)

    # 日付ごとのファイルに保存
    logger.add(
        Path(log_dir) / "{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level=level,
        encoding="utf-8",
        format=_LOG_FORMAT,
    )
