# -*- coding: utf-8 -*-
"""呼叫 LLM 把抓到的新聞整理成繁體中文日報。

模型由環境變數 SUMMARIZER_MODEL 指定，格式 provider:model_id，支援：
    anthropic:claude-opus-4-8（預設）
    openai:gpt-5.5
    google:gemini-3.1-pro-preview
"""
import json
import logging
import os

log = logging.getLogger(__name__)

DEFAULT_MODEL = "anthropic:claude-opus-4-8"
MAX_OUTPUT_TOKENS = 16000

SYSTEM_PROMPT = """\
你是一位資深 AI 產業分析師，為一個 AI 工程團隊撰寫每日 AI 新聞日報。讀者是工程師與技術主管，\
關心：新模型發布、重要研究、開發工具、產業大事、開源社群動態。

你會收到一批過去約 12 小時內抓取的新聞項目（JSON 格式，含標題、來源、連結、原文摘要）。請整理成一份繁體中文日報：

格式要求：
1. 用 Markdown 輸出。最上方先寫 2-3 句「今日重點」總覽。
2. 之後分成這些章節（沒有內容的章節省略）：
   - ## 🔥 重點頭條
   - ## 🧠 模型與研究（官方模型發布、重大技術公告）
   - ## 📄 今日論文（來源為 HF Daily Papers 的項目放這裡；說明研究解決什麼問題、對工程實務的意義）
   - ## 🛠️ 產品與開發工具
   - ## 💼 產業與商業動態
   - ## 🌐 開源與社群（GitHub Trending 的 AI 相關 repo 放這裡，附上當日星數；非 AI 的 repo 直接略過）
3. 每則新聞格式：
   - **中文標題**（自行翻譯，準確且自然）
   - 2-3 句中文摘要：說明發生了什麼、為什麼重要。技術名詞（模型名、公司名、產品名）保留英文原文。
   - 來源連結：[來源名稱](原始 URL)。若項目有 discussion 欄位（HN/Reddit 討論串），在連結後面加上 [討論](discussion URL)。
4. 同一件事被多家報導時合併成一則，連結列出最權威的 1-2 個來源即可。
5. 過濾掉低價值內容：純行銷稿、與 AI 無關、內容農場。寧缺勿濫。
6. 全文使用繁體中文（台灣用語）。

判斷重要性時：官方模型發布 > 重大研究突破 > 主流產品更新 > 融資併購 > 社群討論。\
"""


def _call_anthropic(model: str, user_msg: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        message = stream.get_final_message()
    log.info("tokens: in=%d out=%d", message.usage.input_tokens, message.usage.output_tokens)
    return next(b.text for b in message.content if b.type == "text")


def _call_openai(model: str, user_msg: str) -> str:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    if resp.usage:
        log.info("tokens: in=%d out=%d", resp.usage.prompt_tokens, resp.usage.completion_tokens)
    return resp.choices[0].message.content


def _call_google(model: str, user_msg: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client()  # 讀 GOOGLE_API_KEY / GEMINI_API_KEY
    # google-genai 偶發 "client has been closed" 暫時性錯誤，重試一次即可
    last_exc = None
    for _ in range(3):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_msg,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )
            break
        except Exception as exc:
            last_exc = exc
            log.warning("Gemini 呼叫失敗，重試：%s", exc)
    else:
        raise last_exc
    if resp.usage_metadata:
        log.info(
            "tokens: in=%s out=%s",
            resp.usage_metadata.prompt_token_count,
            resp.usage_metadata.candidates_token_count,
        )
    return resp.text


_PROVIDERS = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
}


def summarize(items: list[dict], edition_label: str) -> str:
    """items -> 繁體中文日報 Markdown。"""
    spec = os.environ.get("SUMMARIZER_MODEL", DEFAULT_MODEL)
    provider, _, model = spec.partition(":")
    if provider not in _PROVIDERS or not model:
        raise ValueError(f"SUMMARIZER_MODEL 格式錯誤：{spec!r}（應為 provider:model_id）")

    payload = json.dumps(items, ensure_ascii=False, indent=1)
    user_msg = (
        f"這是「{edition_label}」的新聞項目，共 {len(items)} 則。"
        f"請整理成日報：\n\n{payload}"
    )

    log.info("呼叫 %s（%s），輸入 %d 則新聞", provider, model, len(items))
    return _PROVIDERS[provider](model, user_msg)
