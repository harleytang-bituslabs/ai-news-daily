"""markdown_to_mrkdwn 轉換器測試。"""
from __future__ import annotations

from ai_news.notify import markdown_to_mrkdwn


def test_headings_become_bold_lines():
    assert markdown_to_mrkdwn("# 今日重點") == "*今日重點*"
    assert markdown_to_mrkdwn("## 🔥 重點頭條") == "*🔥 重點頭條*"
    assert markdown_to_mrkdwn("### 小節") == "*小節*"


def test_bold_converts_to_single_asterisk():
    assert markdown_to_mrkdwn("**OpenAI 發布新模型**") == "*OpenAI 發布新模型*"
    assert markdown_to_mrkdwn("前綴 **粗體** 後綴") == "前綴 *粗體* 後綴"


def test_links_convert_to_slack_format():
    assert markdown_to_mrkdwn("[TechCrunch](https://techcrunch.com/a)") == "<https://techcrunch.com/a|TechCrunch>"
    assert (
        markdown_to_mrkdwn("[來源](https://a.com) 與 [討論](https://b.com)")
        == "<https://a.com|來源> 與 <https://b.com|討論>"
    )


def test_horizontal_rule():
    assert markdown_to_mrkdwn("---") == "──────────"
    assert markdown_to_mrkdwn("-----") == "──────────"


def test_bullets():
    assert markdown_to_mrkdwn("- 第一點") == "• 第一點"
    assert markdown_to_mrkdwn("  - 縮排點") == "  • 縮排點"


def test_code_fence_preserved():
    md = "```\n# 不是標題\n**不是粗體**\n```"
    assert markdown_to_mrkdwn(md) == md


def test_heading_with_bold_and_link():
    assert (
        markdown_to_mrkdwn("## **標題** 見 [連結](https://x.com/a)")
        == "*標題 見 <https://x.com/a|連結>*"
    )


def test_realistic_digest_fragment():
    md = (
        "# AI 日報\n"
        "## 🔥 重點頭條\n"
        "- **OpenAI 發布 GPT-5.5**\n"
        "  三句摘要。[TechCrunch](https://techcrunch.com/gpt) [討論](https://news.ycombinator.com/1)\n"
        "---\n"
    )
    expected = (
        "*AI 日報*\n"
        "*🔥 重點頭條*\n"
        "• *OpenAI 發布 GPT-5.5*\n"
        "  三句摘要。<https://techcrunch.com/gpt|TechCrunch> <https://news.ycombinator.com/1|討論>\n"
        "──────────\n"
    )
    assert markdown_to_mrkdwn(md) == expected.rstrip("\n")
