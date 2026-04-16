"""汎用ユーティリティ関数。"""

from collections.abc import Iterator
from datetime import date, timedelta

__all__ = ["today", "format_date", "date_range"]


def today() -> date:
    """今日の日付を返す。

    Returns:
        今日の date オブジェクト
    """
    return date.today()


def format_date(d: date, fmt: str = "%Y/%m/%d") -> str:
    """date オブジェクトを任意のフォーマットの文字列に変換する。

    Args:
        d: 変換する date オブジェクト
        fmt: strftime フォーマット文字列（デフォルト: "%Y/%m/%d"）

    Returns:
        フォーマット済みの日付文字列

    Examples:
        >>> format_date(date(2026, 4, 16))
        '2026/04/16'
        >>> format_date(date(2026, 4, 16), "%Y-%m-%d")
        '2026-04-16'
        >>> format_date(date(2026, 4, 16), "%Y年%m月%d日")
        '2026年04月16日'
    """
    return d.strftime(fmt)


def date_range(start: date, end: date) -> Iterator[date]:
    """start から end まで（両端含む）の日付を1日ずつ生成するイテレータ。

    Args:
        start: 開始日
        end: 終了日（含む）

    Yields:
        1日刻みの date オブジェクト

    Examples:
        >>> list(date_range(date(2026, 4, 1), date(2026, 4, 3)))
        [date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)]
    """
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
