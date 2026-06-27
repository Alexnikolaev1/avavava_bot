from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import replicate
from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import Settings
from bot.services.media import (
    ReplicateModelFailed,
    ReplicateService,
    TelegramIO,
    compress_for_telegram,
    prepare_face_image,
    prepare_reference_video,
)

log = logging.getLogger(__name__)


@dataclass(slots=True)
class MotionJob:
    chat_id: int
    status_message_id: int
    mode: str
    video_file_id: str
    photo_file_id: str


class MotionService:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        replicate_svc: ReplicateService,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._bot = bot
        self._settings = settings
        self._replicate = replicate_svc
        self._io = TelegramIO(bot)
        self._semaphore = semaphore

    async def safe_edit(self, chat_id: int, message_id: int, text: str) -> None:
        try:
            await self._bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
            )
        except Exception:  # noqa: BLE001
            pass

    async def run(self, job: MotionJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Скачиваю видео и фото...",
                )
                with tempfile.TemporaryDirectory(prefix="motion_") as tmp_str:
                    tmp = Path(tmp_str)
                    raw_video = tmp / "input_raw.mp4"
                    video_path = tmp / "reference.mp4"
                    image_path = tmp / "character.jpg"
                    raw_result = tmp / "result_raw.mp4"
                    final_video = tmp / "result_tg.mp4"

                    await self._io.download_file(job.video_file_id, raw_video)
                    await self._io.download_file(job.photo_file_id, image_path)
                    await prepare_face_image(image_path)

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        "Подготавливаю видео (обрезка, сжатие)...",
                    )
                    await prepare_reference_video(
                        raw_video,
                        video_path,
                        max_seconds=self._settings.motion_max_video_seconds,
                        max_height=self._settings.motion_max_video_height,
                    )

                    status = (
                        "Подменяю персонажа в видео (Wan Animate)..."
                        if job.mode == "replace"
                        else "Переношу движение на твоего персонажа (Kling)..."
                    )
                    await self.safe_edit(job.chat_id, job.status_message_id, status)

                    result_url = await asyncio.wait_for(
                        self._generate(job, video_path, image_path),
                        timeout=self._settings.motion_timeout_seconds,
                    )

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        "Скачиваю результат и сжимаю под Telegram...",
                    )
                    await self._io.download_url(result_url, raw_result)
                    await compress_for_telegram(raw_result, final_video)
                    size = final_video.stat().st_size
                    if size > self._settings.telegram_file_limit_bytes:
                        await compress_for_telegram(
                            raw_result,
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
                            "Попробуй ролик покороче.",
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
                        caption="Готово 💃",
                        supports_streaming=True,
                    )
            except asyncio.TimeoutError:
                log.exception("Motion timed out chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Генерация заняла слишком много времени. Попробуй короче видео.",
                )
            except ReplicateModelFailed as exc:
                log.exception("Motion model failed chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Не удалось создать motion-видео:\n{exc}",
                )
            except replicate.exceptions.ReplicateError as exc:
                log.exception("Motion replicate error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    self._format_replicate_error(exc),
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Motion error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Ошибка motion control: {exc}",
                )

    async def _generate(
        self,
        job: MotionJob,
        video_path: Path,
        image_path: Path,
    ) -> str:
        if job.mode == "replace":
            return await self._wan_replace(video_path, image_path)
        return await self._kling_motion(video_path, image_path)

    async def _wan_replace(self, video_path: Path, image_path: Path) -> str:
        log.info("Motion wan replace model=%s", self._settings.motion_replace_model)
        return await self._replicate.run(
            self._settings.motion_replace_model,
            {
                "video": video_path,
                "character_image": image_path,
                "resolution": self._settings.motion_wan_resolution,
                "go_fast": True,
                "merge_audio": True,
            },
        )

    async def _kling_motion(self, video_path: Path, image_path: Path) -> str:
        inputs: dict[str, Any] = {
            "image": image_path,
            "video": video_path,
            "mode": self._settings.motion_kling_mode,
            "character_orientation": "video",
            "keep_original_sound": True,
            "prompt": "person dancing naturally, smooth motion",
        }
        log.info(
            "Motion kling model=%s mode=%s",
            self._settings.motion_control_model,
            self._settings.motion_kling_mode,
        )
        return await self._replicate.run(self._settings.motion_control_model, inputs)

    @staticmethod
    def _format_replicate_error(exc: replicate.exceptions.ReplicateError) -> str:
        detail = str(exc)
        if "402" in detail or "insufficient credit" in detail.lower():
            return (
                "На Replicate недостаточно кредита (402).\n"
                "Пополни баланс на replicate.com/account/billing"
            )
        return f"Replicate вернул ошибку:\n{exc}"
