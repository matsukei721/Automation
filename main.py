from dotenv import load_dotenv

load_dotenv()

from modules import ConfluenceClient, JiraClient, SlackClient  # noqa: E402


def main() -> None:
    jira = JiraClient()
    confluence = ConfluenceClient()
    slack = SlackClient()

    # 使用例（実際のキーが設定されていれば動作する）
    # issue = jira.get_issue("PROJ-1")
    # page = confluence.get_page("123456")
    # slack.post_message("#general", "Hello from Automation!")

    print("Jira / Confluence / Slack clients initialized.")
    print(f"  Jira     : {jira.base_url}")
    print(f"  Confluence: {confluence.base_url}")
    print(f"  Slack    : Bot token loaded = {bool(slack._token)}")


if __name__ == "__main__":
    main()
