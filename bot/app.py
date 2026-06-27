from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Settings
from bot.handlers import avatar, common, favorites, mascot, motion, photo, photoshoot
from bot.middlewares.access import AccessMiddleware
from bot.services.favorites import FavoritesStore
from bot.services.media import ReplicateService
from bot.services.motion import MotionService
from bot.services.photoshoot import PhotoshootService
from bot.services.pipeline import GenerationPipeline

log = logging.getLogger(__name__)


def create_app(settings: Settings) -> tuple[Dispatcher, GenerationPipeline, FavoritesStore]:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
    replicate = ReplicateService(settings)
    pipeline = GenerationPipeline(bot=bot, settings=settings, semaphore=semaphore)
    photoshoot_service = PhotoshootService(
        bot=bot,
        settings=settings,
        replicate=replicate,
        semaphore=semaphore,
    )
    motion_service = MotionService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        semaphore=semaphore,
    )
    favorites_store = FavoritesStore(
        db_path=Path(settings.database_path),
        max_per_user=settings.max_favorites_per_user,
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp["pipeline"] = pipeline
    dp["settings"] = settings
    dp["favorites"] = favorites_store
    dp["photoshoot"] = photoshoot_service
    dp["motion"] = motion_service

    router = Router()
    access = AccessMiddleware()
    router.message.middleware(access)
    router.callback_query.middleware(access)
    router.include_router(common.router)
    router.include_router(favorites.router)
    router.include_router(avatar.router)
    router.include_router(photo.router)
    router.include_router(mascot.router)
    router.include_router(photoshoot.router)
    router.include_router(motion.router)
    dp.include_router(router)
    return dp, pipeline, favorites_store
