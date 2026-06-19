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
from bot.models.avatar_config import AvatarConfig
from bot.services.media import (
    AvatarGenerator,
    ReplicateService,
    SadTalkerService,
    TelegramIO,
    compress_for_telegram,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class AvatarJob:
    chat_id: int
    status_message_id: int
    config: AvatarConfig
    prompt: str | None = None


@dataclass(slots=True)
class VideoJob:
    chat_id: int
    status_message_id: int
    image_file_id: str
    audio_file_id: str
    audio_duration: int | None = None
    cartoon: bool = True


class GenerationPipeline:
    def __init__(self, bot: Bot, settings: Settings, semaphore: asyncio.Semaphore) -> None:
        self.bot = bot
        self._bot = bot
        self._settings = settings
        self._semaphore = semaphore
        self._io = TelegramIO(bot)
        replicate_svc = ReplicateService(settings)
        self._avatar_gen = AvatarGenerator(replicate_svc, settings)
        self._sadtalker = SadTalkerService(replicate_svc, settings)
        self._active_jobs = 0

    @property
    def active_jobs(self) -> int:
        return self._active_jobs

    @property
    def max_concurrent_jobs(self) -> int:
        return self._settings.max_concurrent_jobs

    async def safe_edit(self, chat_id: int, message_id: int, text: str) -> None:
        try:
            await self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
            )
        except Exception:  # noqa: BLE001
            pass

    async def generate_avatar(self, job: AvatarJob) -> str | None:
        async with self._semaphore:
            self._active_jobs += 1
            try:
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Рисую мультяшного персонажа...",
                )
                with tempfile.TemporaryDirectory(prefix="avatar_draw_") as tmp_str:
                    tmp = Path(tmp_str)
                    image_path = tmp / "avatar.png"
                    prompt = job.prompt or job.config.to_prompt()
                    await asyncio.wait_for(
                        self._avatar_gen.generate(prompt, image_path),
                        timeout=self._settings.avatar_generation_timeout_seconds,
                    )
                    caption = f"Персонаж готов! 🎨\n<i>{job.config.summary()}</i>"
                    sent = await self._bot.send_photo(
                        chat_id=job.chat_id,
                        photo=FSInputFile(image_path),
                        caption=caption,
                    )
                    return sent.photo[-1].file_id
            except asyncio.TimeoutError:
                log.exception("Avatar generation timed out chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Рисование заняло слишком много времени. Попробуй ещё раз.",
                )
            except replicate.exceptions.ReplicateError as exc:
                log.exception("Replicate avatar error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Не удалось нарисовать персонажа: {exc}",
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Avatar error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Ошибка при создании персонажа: {exc}",
                )
            finally:
                self._active_jobs -= 1
        return None

    async def regenerate_from_config(
        self,
        chat_id: int,
        config: AvatarConfig,
        *,
        status_message_id: int | None = None,
    ) -> str | None:
        status_id = status_message_id
        if status_id is None:
            msg = await self._bot.send_message(chat_id, "Обновляю изображение персонажа...")
            status_id = msg.message_id
        job = AvatarJob(chat_id=chat_id, status_message_id=status_id, config=config)
        return await self.generate_avatar(job)

    async def generate_video(self, job: VideoJob) -> None:
        async with self._semaphore:
            self._active_jobs += 1
            try:
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Скачиваю файлы...",
                )
                with tempfile.TemporaryDirectory(prefix="avatar_video_") as tmp_str:
                    tmp = Path(tmp_str)
                    image_path = tmp / "face.png"
                    audio_path = tmp / "voice.ogg"
                    raw_video = tmp / "raw.mp4"
                    final_video = tmp / "final.mp4"

                    await self._io.download_file(job.image_file_id, image_path)
                    await self._io.download_file(job.audio_file_id, audio_path)

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        "Оживляю персонажа (lip-sync)...",
                    )
                    result_url = await asyncio.wait_for(
                        self._sadtalker.animate(
                            image_path,
                            audio_path,
                            cartoon=job.cartoon,
                        ),
                        timeout=self._settings.generation_timeout_seconds,
                    )
                    await self._io.download_url(result_url, raw_video)

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        "Сжимаю видео под лимиты Telegram...",
                    )
                    await compress_for_telegram(raw_video, final_video)
                    size = final_video.stat().st_size
                    if size > self._settings.telegram_file_limit_bytes:
                        await compress_for_telegram(
                            raw_video,
                            final_video,
                            crf=34,
                            scale_height=480,
                        )
                        size = final_video.stat().st_size

                    if size > self._settings.telegram_file_limit_bytes:
                        await self.safe_edit(
                            job.chat_id,
                            job.status_message_id,
                            "Видео больше 50 МБ даже после сжатия. "
                            "Попробуй аудио покороче или другого персонажа.",
                        )
                        return

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        "Готово! Отправляю видео...",
                    )
                    await self._bot.send_video(
                        chat_id=job.chat_id,
                        video=FSInputFile(final_video),
                        caption="Готово 🎬",
                        supports_streaming=True,
                    )
            except asyncio.TimeoutError:
                log.exception("Video generation timed out chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Генерация заняла слишком много времени. Попробуй ещё раз.",
                )
            except replicate.exceptions.ReplicateError as exc:
                log.exception("Replicate video error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Сервис генерации вернул ошибку. "
                    "Попробуй перегенерировать аватар или другое фото.\n"
                    f"Детали: {exc}",
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Video error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Не получилось сгенерировать видео: {exc}",
                )
            finally:
                self._active_jobs -= 1
