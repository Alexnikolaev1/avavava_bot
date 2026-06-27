from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Settings
from bot.handlers import (
    avatar,
    common,
    creative,
    favorites,
    history,
    hub,
    i2v,
    mascot,
    motion,
    photo,
    photoshoot,
    pipeline,
    singing,
    subtitles,
)
from bot.middlewares.access import AccessMiddleware
from bot.services.creative import CreativeService
from bot.services.favorites import FavoritesStore
from bot.services.history import HistoryStore
from bot.services.i2v import I2VService
from bot.services.media import ReplicateService
from bot.services.motion import MotionService
from bot.services.pending import PendingStore
from bot.services.photoshoot import PhotoshootService
from bot.services.pipeline import GenerationPipeline
from bot.services.singing import SingingService
from bot.services.stickers import StickerService
from bot.services.subtitles import SubtitlesService
from bot.services.voice import VoiceService

log = logging.getLogger(__name__)


def create_app(
    settings: Settings,
) -> tuple[Dispatcher, GenerationPipeline, FavoritesStore, HistoryStore]:
    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
    replicate = ReplicateService(settings)
    db_path = Path(settings.database_path)

    history_store = HistoryStore(db_path=db_path, max_per_user=settings.max_history_per_user)
    pipeline = GenerationPipeline(bot=bot, settings=settings, semaphore=semaphore)
    photoshoot_service = PhotoshootService(
        bot=bot,
        settings=settings,
        replicate=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    motion_service = MotionService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    creative_service = CreativeService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    i2v_service = I2VService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    voice_service = VoiceService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    singing_service = SingingService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    sticker_service = StickerService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    subtitles_service = SubtitlesService(
        bot=bot,
        settings=settings,
        replicate_svc=replicate,
        history=history_store,
        semaphore=semaphore,
    )
    favorites_store = FavoritesStore(
        db_path=db_path,
        max_per_user=settings.max_favorites_per_user,
    )
    pending_store = PendingStore()

    dp = Dispatcher(storage=MemoryStorage())
    dp["pipeline"] = pipeline
    dp["settings"] = settings
    dp["favorites"] = favorites_store
    dp["history"] = history_store
    dp["pending"] = pending_store
    dp["photoshoot"] = photoshoot_service
    dp["motion"] = motion_service
    dp["creative"] = creative_service
    dp["i2v"] = i2v_service
    dp["voice"] = voice_service
    dp["singing"] = singing_service
    dp["stickers"] = sticker_service
    dp["subtitles"] = subtitles_service

    router = Router()
    access = AccessMiddleware()
    router.message.middleware(access)
    router.callback_query.middleware(access)
    router.include_router(hub.router)
    router.include_router(pipeline.router)
    router.include_router(history.router)
    router.include_router(common.router)
    router.include_router(favorites.router)
    router.include_router(avatar.router)
    router.include_router(photo.router)
    router.include_router(mascot.router)
    router.include_router(photoshoot.router)
    router.include_router(motion.router)
    router.include_router(creative.router)
    router.include_router(i2v.router)
    router.include_router(singing.router)
    router.include_router(subtitles.router)
    dp.include_router(router)
    return dp, pipeline, favorites_store, history_store
