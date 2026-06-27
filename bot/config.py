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


def _parse_user_ids(raw: str | None) -> frozenset[int]:
    if not raw or not raw.strip():
        return frozenset()
    ids: set[int] = set()
    for chunk in raw.replace(";", ",").split(","):
        part = chunk.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    replicate_api_token: str
    avatar_model: str
    sadtalker_model: str
    kling_avatar_model: str
    kling_avatar_mode: str
    max_audio_seconds: int
    max_concurrent_jobs: int
    user_cooldown_seconds: int
    generation_timeout_seconds: int
    avatar_generation_timeout_seconds: int
    photoshoot_timeout_seconds: int
    photoshoot_headshot_model: str
    photoshoot_style_model: str
    photoshoot_custom_model: str
    motion_timeout_seconds: int
    motion_max_video_seconds: int
    motion_max_video_height: int
    motion_replace_model: str
    motion_control_model: str
    motion_kling_mode: str
    motion_wan_resolution: str
    max_favorites_per_user: int
    database_path: str
    log_level: str
    allowed_user_ids: frozenset[int]

    telegram_file_limit_bytes: int = 49 * 1024 * 1024

    def is_user_allowed(self, user_id: int) -> bool:
        if not self.allowed_user_ids:
            return True
        return user_id in self.allowed_user_ids

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
            replicate_api_token=_require("REPLICATE_API_TOKEN"),
            avatar_model=os.environ.get(
                "AVATAR_MODEL",
                "black-forest-labs/flux-schnell",
            ),
            sadtalker_model=os.environ.get(
                "SADTALKER_MODEL",
                "lucataco/sadtalker:85c698db7c0a66d5011435d0191db323034e1da04b912a6d365833141b6a285b",
            ),
            kling_avatar_model=os.environ.get(
                "KLING_AVATAR_MODEL",
                "kwaivgi/kling-avatar-v2",
            ),
            kling_avatar_mode=os.environ.get("KLING_AVATAR_MODE", "std"),
            max_audio_seconds=_int("MAX_AUDIO_SECONDS", 75),
            max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 2),
            user_cooldown_seconds=_int("USER_COOLDOWN_SECONDS", 60),
            generation_timeout_seconds=_int("GENERATION_TIMEOUT_SECONDS", 600),
            avatar_generation_timeout_seconds=_int("AVATAR_GENERATION_TIMEOUT_SECONDS", 120),
            photoshoot_timeout_seconds=_int("PHOTOSHOOT_TIMEOUT_SECONDS", 180),
            photoshoot_headshot_model=os.environ.get(
                "PHOTOSHOOT_HEADSHOT_MODEL",
                "flux-kontext-apps/professional-headshot",
            ),
            photoshoot_style_model=os.environ.get(
                "PHOTOSHOOT_STYLE_MODEL",
                "fofr/face-to-many:edc6439ac55af138defbca7c472b38bcdd62c61797e8e0c2fae88696cd8afb25",
            ),
            photoshoot_custom_model=os.environ.get(
                "PHOTOSHOOT_CUSTOM_MODEL",
                "mbukerepo/photomaker",
            ),
            motion_timeout_seconds=_int("MOTION_TIMEOUT_SECONDS", 900),
            motion_max_video_seconds=_int("MOTION_MAX_VIDEO_SECONDS", 15),
            motion_max_video_height=_int("MOTION_MAX_VIDEO_HEIGHT", 720),
            motion_replace_model=os.environ.get(
                "MOTION_REPLACE_MODEL",
                "wan-video/wan-2.2-animate-replace",
            ),
            motion_control_model=os.environ.get(
                "MOTION_CONTROL_MODEL",
                "kwaivgi/kling-v3-motion-control",
            ),
            motion_kling_mode=os.environ.get(
                "MOTION_KLING_MODE",
                os.environ.get("KLING_AVATAR_MODE", "std"),
            ),
            motion_wan_resolution=os.environ.get("MOTION_WAN_RESOLUTION", "480"),
            max_favorites_per_user=_int("MAX_FAVORITES_PER_USER", 10),
            database_path=os.environ.get("DATABASE_PATH", "data/bot.db"),
            log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
            allowed_user_ids=_parse_user_ids(os.environ.get("ALLOWED_USER_IDS")),
        )


settings = Settings.from_env()
