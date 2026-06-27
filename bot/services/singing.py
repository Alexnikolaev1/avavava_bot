from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import replicate
from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import Settings
from bot.services.history import HistoryStore
from bot.services.media import (
    KlingAvatarService,
    ReplicateModelFailed,
    ReplicateService,
    TelegramIO,
    compress_for_telegram,
    convert_audio_for_kling,
    prepare_face_image,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class SingingJob:
    chat_id: int
    user_id: int
    status_message_id: int
    photo_file_id: str
    audio_file_id: str


class SingingService:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        replicate_svc: ReplicateService,
        history: HistoryStore,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._bot = bot
        self._settings = settings
        self._replicate = replicate_svc
        self._kling = KlingAvatarService(replicate_svc, settings)
        self._io = TelegramIO(bot)
        self._history = history
        self._semaphore = semaphore

    async def safe_edit(self, chat_id: int, message_id: int, text: str) -> None:
        try:
            await self._bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
        except Exception:  # noqa: BLE001
            pass

    async def run(self, job: SingingJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(
                    job.chat_id, job.status_message_id,
                    "Создаю поющий аватар (Kling)...",
                )
                with tempfile.TemporaryDirectory(prefix="singing_") as tmp_str:
                    tmp = Path(tmp_str)
                    image = tmp / "face.jpg"
                    audio_in = tmp / "audio_in"
                    raw = tmp / "raw.mp4"
                    final = tmp / "final.mp4"

                    await self._io.download_file(job.photo_file_id, image)
                    await self._io.download_file(job.audio_file_id, audio_in)
                    await prepare_face_image(image)

                    url = await asyncio.wait_for(
                        self._kling.animate(image, audio_in),
                        timeout=self._settings.generation_timeout_seconds,
                    )
                    await self._io.download_url(url, raw)
                    await compress_for_telegram(raw, final)

                    sent = await self._bot.send_video(
                        job.chat_id,
                        video=FSInputFile(final),
                        caption="Готово 🎤",
                        supports_streaming=True,
                    )
                    video_id = sent.video.file_id
                    item = await self._history.add(
                        job.user_id,
                        "singing",
                        "Поющий аватар",
                        image_file_id=job.photo_file_id,
                        audio_file_id=job.audio_file_id,
                        video_file_id=video_id,
                    )
                    from bot.keyboards import video_pipeline_keyboard
                    await self._bot.send_message(
                        job.chat_id,
                        "Что дальше?",
                        reply_markup=video_pipeline_keyboard(item.id),
                    )
            except asyncio.TimeoutError:
                await self.safe_edit(job.chat_id, job.status_message_id, "Таймаут.")
            except ReplicateModelFailed as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка:\n{exc}")
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Replicate:\n{exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("Singing error")
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка: {exc}")
