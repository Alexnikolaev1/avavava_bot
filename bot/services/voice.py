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
from bot.services.media import ReplicateModelFailed, ReplicateService, TelegramIO, convert_audio_to_wav

log = logging.getLogger(__name__)


@dataclass(slots=True)
class VoiceJob:
    chat_id: int
    user_id: int
    status_message_id: int
    sample_file_id: str
    text: str
    language: str = "ru"


class VoiceService:
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

    async def run(self, job: VoiceJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(job.chat_id, job.status_message_id, "Клонирую голос и озвучиваю текст...")
                with tempfile.TemporaryDirectory(prefix="voice_") as tmp_str:
                    tmp = Path(tmp_str)
                    sample = tmp / "sample.wav"
                    raw_out = tmp / "output.wav"
                    mp3_out = tmp / "output.mp3"

                    await self._io.download_file(job.sample_file_id, tmp / "sample_in")
                    await convert_audio_to_wav(tmp / "sample_in", sample)

                    url = await asyncio.wait_for(
                        self._replicate.run(
                            self._settings.voice_clone_model,
                            {
                                "text": job.text,
                                "speaker": sample,
                                "language": job.language,
                                "cleanup_voice": True,
                            },
                        ),
                        timeout=self._settings.voice_timeout_seconds,
                    )
                    await self._io.download_url(url, raw_out)

                    from bot.services.media import convert_audio_for_kling
                    await convert_audio_for_kling(raw_out, mp3_out)

                    sent = await self._bot.send_audio(
                        job.chat_id,
                        audio=FSInputFile(mp3_out),
                        caption="Готово 🎙",
                    )
                    audio_id = sent.audio.file_id
                    item = await self._history.add(
                        job.user_id,
                        "voice",
                        job.text[:50],
                        audio_file_id=audio_id,
                        meta={"language": job.language, "text": job.text},
                    )
                    from bot.keyboards import audio_pipeline_keyboard
                    await self._bot.send_message(
                        job.chat_id,
                        "Озвучка готова. Можно сразу оживить персонажа:",
                        reply_markup=audio_pipeline_keyboard(item.id),
                    )
            except asyncio.TimeoutError:
                await self.safe_edit(job.chat_id, job.status_message_id, "Таймаут озвучки.")
            except ReplicateModelFailed as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка:\n{exc}")
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Replicate:\n{exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("Voice error")
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка: {exc}")
