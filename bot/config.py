from __future__ import annotations

import os
from dataclasses import dataclass


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Переменная окружения {name} обязательна")
    return value


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    replicate_api_token: str
    avatar_model: str
    sadtalker_model: str
    max_audio_seconds: int
    max_concurrent_jobs: int
    user_cooldown_seconds: int
    generation_timeout_seconds: int
    avatar_generation_timeout_seconds: int
    max_favorites_per_user: int
    database_path: str
    log_level: str

    telegram_file_limit_bytes: int = 49 * 1024 * 1024

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
            replicate_api_token=_require("REPLICATE_API_TOKEN"),
            avatar_model=os.environ.get(
                "AVATAR_MODEL",
                "black-forest-labs/flux-schnell",
            ),
            sadtalker_model=os.environ.get("SADTALKER_MODEL", "cjwbw/sadtalker"),
            max_audio_seconds=_int("MAX_AUDIO_SECONDS", 75),
            max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 2),
            user_cooldown_seconds=_int("USER_COOLDOWN_SECONDS", 60),
            generation_timeout_seconds=_int("GENERATION_TIMEOUT_SECONDS", 600),
            avatar_generation_timeout_seconds=_int("AVATAR_GENERATION_TIMEOUT_SECONDS", 120),
            max_favorites_per_user=_int("MAX_FAVORITES_PER_USER", 10),
            database_path=os.environ.get("DATABASE_PATH", "data/bot.db"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        )


settings = Settings.from_env()
