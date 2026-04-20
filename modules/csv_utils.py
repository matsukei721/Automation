"""CSV ファイル読み込みユーティリティ。"""

import csv
from pathlib import Path

from loguru import logger


def read_csv(
    file_path: str | Path,
    encoding: str = "utf-8",
) -> list[dict[str, str]]:
    """CSV ファイルを読み込み、辞書のリストで返す。

    1行目をヘッダーとして扱い、各行を辞書に変換します。

    Args:
        file_path: CSV ファイルパス
        encoding: ファイルエンコーディング（デフォルト: utf-8、日本語Excelの場合は cp932）

    Returns:
        [{"column1": "value1", "column2": "value2"}, ...]

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: CSV が読み込めない場合
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV ファイルが見つかりません: {file_path}")

    logger.info("read_csv | file_path={} encoding={}", file_path, encoding)

    try:
        with file_path.open(encoding=encoding) as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise ValueError("CSV が空または形式が不正です")

            rows = list(reader)
            logger.info("read_csv | done | rows={}", len(rows))
            return rows
    except UnicodeDecodeError as e:
        logger.error("read_csv | エンコーディングエラー: {}", e)
        raise ValueError(
            f"ファイルの読み込みに失敗しました。エンコーディングを確認してください: {e}"
        ) from e
    except Exception as e:
        logger.error("read_csv | エラー: {}", e)
        raise


def read_csv_rows(
    file_path: str | Path,
    encoding: str = "utf-8",
    skip_header: bool = True,
) -> list[list[str]]:
    """CSV ファイルを読み込み、行のリストで返す。

    Args:
        file_path: CSV ファイルパス
        encoding: ファイルエンコーディング（デフォルト: utf-8、日本語Excelの場合は cp932）
        skip_header: True の場合は1行目（ヘッダー）をスキップ

    Returns:
        [["val1", "val2"], ["val3", "val4"], ...]

    Raises:
        FileNotFoundError: ファイルが見つからない場合
        ValueError: CSV が読み込めない場合
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV ファイルが見つかりません: {file_path}")

    logger.info(
        "read_csv_rows | file_path={} encoding={} skip_header={}", file_path, encoding, skip_header
    )

    try:
        with file_path.open(encoding=encoding) as f:
            reader = csv.reader(f)
            if skip_header:
                next(reader)

            rows = list(reader)
            logger.info("read_csv_rows | done | rows={}", len(rows))
            return rows
    except UnicodeDecodeError as e:
        logger.error("read_csv_rows | エンコーディングエラー: {}", e)
        raise ValueError(
            f"ファイルの読み込みに失敗しました。エンコーディングを確認してください: {e}"
        ) from e
    except Exception as e:
        logger.error("read_csv_rows | エラー: {}", e)
        raise


def validate_csv_row(row: list[str], expected_length: int) -> bool:
    """CSV 行の要素数をチェックする。

    Args:
        row: CSV の1行（リスト）
        expected_length: 期待される列数

    Returns:
        要素数が一致すれば True、そうでなければ False
    """
    return len(row) == expected_length
