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
    ReplicateModelFailed,
    ReplicateService,
    TelegramIO,
    compress_for_telegram,
    prepare_face_image,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class I2VJob:
    chat_id: int
    user_id: int
    status_message_id: int
    photo_file_id: str
    prompt: str
    duration: int = 5


class I2VService:
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
        self._io = TelegramIO(bot)
        self._history = history
        self._semaphore = semaphore

    async def safe_edit(self, chat_id: int, message_id: int, text: str) -> None:
        try:
            await self._bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
        except Exception:  # noqa: BLE001
            pass

    async def run(self, job: I2VJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(job.chat_id, job.status_message_id, "Генерирую видео по промпту...")
                with tempfile.TemporaryDirectory(prefix="i2v_") as tmp_str:
                    tmp = Path(tmp_str)
                    image = tmp / "start.jpg"
                    raw = tmp / "raw.mp4"
                    final = tmp / "final.mp4"
                    await self._io.download_file(job.photo_file_id, image)
                    await prepare_face_image(image)

                    url = await asyncio.wait_for(
                        self._replicate.run(
                            self._settings.i2v_model,
                            {
                                "prompt": job.prompt,
                                "start_image": image,
                                "duration": job.duration,
                                "mode": self._settings.i2v_mode,
                                "negative_prompt": "blurry, distorted, low quality",
                            },
                        ),
                        timeout=self._settings.i2v_timeout_seconds,
                    )
                    await self._io.download_url(url, raw)
                    await compress_for_telegram(raw, final)

                    sent = await self._bot.send_video(
                        job.chat_id,
                        video=FSInputFile(final),
                        caption="Готово 🎥",
                        supports_streaming=True,
                    )
                    video_id = sent.video.file_id
                    item = await self._history.add(
                        job.user_id,
                        "i2v",
                        job.prompt[:60],
                        image_file_id=job.photo_file_id,
                        video_file_id=video_id,
                        meta={"prompt": job.prompt, "duration": job.duration},
                    )
                    from bot.keyboards import video_pipeline_keyboard
                    await self._bot.send_message(
                        job.chat_id,
                        "Что дальше?",
                        reply_markup=video_pipeline_keyboard(item.id),
                    )
            except asyncio.TimeoutError:
                await self.safe_edit(
                    job.chat_id, job.status_message_id, "Таймаут генерации видео.",
                )
            except ReplicateModelFailed as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка:\n{exc}")
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Replicate:\n{exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("I2V error")
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка: {exc}")
