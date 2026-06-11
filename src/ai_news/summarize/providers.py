"""LLM provider 介接層。

每個 provider 是一個 (model, system, user) -> str 的函式；
新增供應商：實作同簽名的函式並登錄到 PROVIDERS。
SDK 採延遲 import，避免沒用到的供應商成為硬相依。
"""
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 16000

CompleteFn = Callable[[str, str, str], str]


def _anthropic(model: str, system: str, user: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=model,
        max_tokens=MAX_OUTPUT_TOKENS,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        message = stream.get_final_message()
    log.info("tokens: in=%d out=%d", message.usage.input_tokens, message.usage.output_tokens)
    return next(block.text for block in message.content if block.type == "text")


def _openai(model: str, system: str, user: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        max_completion_tokens=MAX_OUTPUT_TOKENS,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    if resp.usage:
        log.info("tokens: in=%d out=%d", resp.usage.prompt_tokens, resp.usage.completion_tokens)
    return resp.choices[0].message.content or ""


def _google(model: str, system: str, user: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client()  # 讀 GOOGLE_API_KEY / GEMINI_API_KEY
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
    # google-genai 偶發 "client has been closed" 暫時性錯誤，重試即可
    last_exc: Exception = RuntimeError("unreachable")
    for _ in range(3):
        try:
            resp = client.models.generate_content(model=model, contents=user, config=config)
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
    return resp.text or ""


PROVIDERS: dict[str, CompleteFn] = {
    "anthropic": _anthropic,
    "openai": _openai,
    "google": _google,
}
