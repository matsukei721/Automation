import traceback

import yaml
from dotenv import load_dotenv

load_dotenv()

from loguru import logger  # noqa: E402

from modules import ConfluenceClient, JiraClient, SlackClient, setup_logger  # noqa: E402

setup_logger()


def _load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    config = _load_config()
    notify_channel = config.get("slack", {}).get("notify_channel", "#general")

    slack = SlackClient()

    try:
        logger.info("=== Automation start ===")

        _jira = JiraClient.from_config()
        _confluence = ConfluenceClient.from_config()

        # ここに各処理を追加していく
        # 例:
        # issues = _jira.search_issues("project = PROJ AND status = 'In Progress'")
        # _confluence.insert_row_below_header([...])

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
