"""Точка входа: python main.py"""

from __future__ import annotations

import asyncio
import logging
import sys

from bot.app import create_app
from bot.config import settings


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )


async def main() -> None:
    setup_logging(settings.log_level)
    log = logging.getLogger("main")
    dp, pipeline, favorites = create_app(settings)
    await favorites.connect()

    log.info(
        "Bot started | jobs=%s | favorites=%s | avatar=%s | sadtalker=%s | kling=%s",
        settings.max_concurrent_jobs,
        settings.max_favorites_per_user,
        settings.avatar_model,
        settings.sadtalker_model,
        settings.kling_avatar_model,
    )
    if settings.allowed_user_ids:
        log.info("Access whitelist: %d user(s)", len(settings.allowed_user_ids))
    else:
        log.warning("ALLOWED_USER_IDS not set — bot is open to all users")
    try:
        await dp.start_polling(pipeline.bot)
    finally:
        await favorites.close()


if __name__ == "__main__":
    asyncio.run(main())
