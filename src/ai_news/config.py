"""組態：環境變數、模型規格、執行參數。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL_SPEC = "anthropic:claude-opus-4-8"
DEFAULT_WINDOW_HOURS = 13  # 12 小時排程 + 1 小時緩衝
DEFAULT_MAX_ITEMS = 40
DEFAULT_TIMEZONE = "America/Los_Angeles"

PROVIDERS = ("anthropic", "openai", "google")


@dataclass(frozen=True)
class ModelSpec:
    """LLM 模型規格，格式 provider:model_id。"""

    provider: str
    model: str

    @classmethod
    def parse(cls, spec: str) -> ModelSpec:
        provider, _, model = spec.partition(":")
        if provider not in PROVIDERS or not model:
            raise ValueError(
                f"模型規格錯誤：{spec!r}（應為 provider:model_id，provider ∈ {PROVIDERS}）"
            )
        return cls(provider=provider, model=model)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class Settings:
    base_dir: Path
    model: ModelSpec
    window_hours: int = DEFAULT_WINDOW_HOURS
    max_items: int = DEFAULT_MAX_ITEMS
    timezone: str = DEFAULT_TIMEZONE
    slack_webhook: str | None = None

    @property
    def reports_dir(self) -> Path:
        return self.base_dir / "reports"

    @property
    def raw_data_dir(self) -> Path:
        return self.base_dir / "data" / "raw"

    @classmethod
    def from_env(
        cls,
        base_dir: Path,
        window_hours: int | None = None,
        max_items: int | None = None,
    ) -> Settings:
        return cls(
            base_dir=base_dir,
            model=ModelSpec.parse(os.environ.get("SUMMARIZER_MODEL", DEFAULT_MODEL_SPEC)),
            window_hours=window_hours or DEFAULT_WINDOW_HOURS,
            max_items=max_items or DEFAULT_MAX_ITEMS,
            timezone=os.environ.get("REPORT_TZ", DEFAULT_TIMEZONE),
            slack_webhook=os.environ.get("SLACK_WEBHOOK_URL"),
        )


def load_dotenv(base_dir: Path) -> None:
    """讀取 base_dir/.env（KEY=VALUE），不覆蓋已存在的環境變數。"""
    env_file = base_dir / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))
