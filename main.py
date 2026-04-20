import traceback
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from loguru import logger  # noqa: E402

from modules import (  # noqa: E402
    ConfluenceClient,
    ExcelClient,
    JiraClient,
    SlackClient,
    setup_logger,
)
from modules.csv_utils import read_csv_rows, validate_csv_row  # noqa: E402
from modules.utils import load_config  # noqa: E402

setup_logger()


def main() -> None:
    config = load_config()
    notify_channel = config.get("slack", {}).get("notify_channel", "#general")

    slack = SlackClient()

    try:
        logger.info("=== Automation start ===")

        # クライアント生成（config.yaml の account_mode・scope に基づく）
        _jira = JiraClient.from_config()
        _confluence = ConfluenceClient.from_config()
        excel = ExcelClient.from_config()

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 例1: CSV から Excel に自動書き込み
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        csv_file = Path(config.get("csv", {}).get("input_file", "input.csv"))
        csv_encoding = config.get("csv", {}).get("encoding", "utf-8")

        if csv_file.exists():
            logger.info("CSV ファイルを読み込み中: {}", csv_file)
            csv_rows = read_csv_rows(csv_file, encoding=csv_encoding)

            expected_cols = (
                ord(excel.default_end_col.upper()) - ord(excel.default_start_col.upper()) + 1
            )

            for idx, row in enumerate(csv_rows, start=1):
                if not validate_csv_row(row, expected_cols):
                    logger.warning(
                        "CSV 行 {} の列数が不正です: 期待 {} 列、実際 {} 列。スキップ",
                        idx,
                        expected_cols,
                        len(row),
                    )
                    continue

                target_date = row[0]

                try:
                    excel.write_row_by_date(data=row, target_date=target_date)
                    logger.info("Excel に書き込み: 日付={} 行={}", target_date, idx)
                except ValueError as e:
                    logger.warning("Excel 書き込みをスキップ: {}", e)
                except Exception as e:
                    logger.error("Excel 書き込みエラー: {}", e)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 例2: CSV から Confluence テーブルに自動追記
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # if csv_file.exists():
        #     for idx, row in enumerate(read_csv_rows(csv_file, encoding=csv_encoding), start=1):
        #         try:
        #             confluence.insert_row_below_header([str(cell) for cell in row])
        #             logger.info("Confluence テーブルに追記: 行={}", idx)
        #         except Exception as e:
        #             logger.error("Confluence 追記エラー: {}", e)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 例3: CSV から Jira Issue を作成
        # CSV の形式: [プロジェクトキー, サマリー, 説明, Issue タイプ]
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # if csv_file.exists():
        #     for idx, row in enumerate(read_csv_rows(csv_file, encoding=csv_encoding), start=1):
        #         if len(row) < 2:
        #             logger.warning("CSV 行 {} に不足データがあります。スキップ", idx)
        #             continue
        #         try:
        #             issue = jira.create_issue(
        #                 project_key=row[0],
        #                 summary=row[1],
        #                 description=row[2] if len(row) > 2 else "",
        #                 issue_type=row[3] if len(row) > 3 else "Task",
        #             )
        #             logger.info("Jira Issue 作成: key={}", issue.get("key"))
        #         except Exception as e:
        #             logger.error("Jira Issue 作成エラー: {}", e)

        logger.info("=== Automation complete ===")
        slack.notify_success(notify_channel, "Automation 実行完了")

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Automation failed: {}\n{}", e, tb)
        try:
            slack.notify_error(notify_channel, "Automation 実行失敗", e, tb)
        except Exception as slack_err:
            logger.error("Slack通知にも失敗しました: {}", slack_err)
        raise


if __name__ == "__main__":
    main()
