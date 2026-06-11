"""把新聞素材整理成繁體中文日報。"""
from __future__ import annotations

import json
import logging

from ai_news.config import ModelSpec
from ai_news.models import NewsItem
from ai_news.summarize.prompt import SYSTEM_PROMPT
from ai_news.summarize.providers import PROVIDERS

log = logging.getLogger(__name__)


def summarize(items: list[NewsItem], edition_label: str, spec: ModelSpec) -> str:
    payload = json.dumps([item.to_payload() for item in items], ensure_ascii=False, indent=1)
    user_msg = f"這是「{edition_label}」的新聞項目，共 {len(items)} 則。請整理成日報：\n\n{payload}"

    log.info("呼叫 %s，輸入 %d 則新聞", spec, len(items))
    return PROVIDERS[spec.provider](spec.model, SYSTEM_PROMPT, user_msg)
