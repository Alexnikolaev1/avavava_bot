from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

import replicate
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto

from bot.config import Settings
from bot.photoshoot_catalog import FACE_TO_MANY_STYLES
from bot.services.history import HistoryStore
from bot.services.media import ReplicateModelFailed, ReplicateService, TelegramIO

log = logging.getLogger(__name__)

STICKER_STYLES = ("emoji", "pixel", "toy", "3d")


@dataclass(slots=True)
class StickerJob:
    chat_id: int
    user_id: int
    status_message_id: int
    photo_file_id: str


class StickerService:
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

    async def run(self, job: StickerJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(job.chat_id, job.status_message_id, "Рисую стикеры...")
                with tempfile.TemporaryDirectory(prefix="stickers_") as tmp_str:
                    tmp = Path(tmp_str)
                    source = tmp / "source.jpg"
                    await self._io.download_file(job.photo_file_id, source)

                    stickers: list[Path] = []
                    for idx, style_key in enumerate(STICKER_STYLES):
                        await self.safe_edit(
                            job.chat_id,
                            job.status_message_id,
                            f"Стикер {idx + 1}/{len(STICKER_STYLES)}...",
                        )
                        style_value, prompt_suffix = FACE_TO_MANY_STYLES[style_key]
                        urls = await asyncio.wait_for(
                            self._replicate.run_many(
                                self._settings.photoshoot_style_model,
                                {
                                    "image": source,
                                    "style": style_value,
                                    "prompt": f"sticker, {prompt_suffix}, transparent background",
                                    "instant_id_strength": 0.9,
                                    "denoising_strength": 0.6,
                                },
                            ),
                            timeout=self._settings.photoshoot_timeout_seconds,
                        )
                        if not urls:
                            continue
                        raw = tmp / f"raw_{idx}.png"
                        await self._io.download_url(urls[0], raw)
                        sticker = tmp / f"sticker_{idx}.webp"
                        await self._to_sticker(raw, sticker)
                        stickers.append(sticker)

                    if not stickers:
                        await self.safe_edit(
                            job.chat_id, job.status_message_id, "Не удалось создать стикеры.",
                        )
                        return

                    media = [InputMediaPhoto(media=FSInputFile(p)) for p in stickers[:10]]
                    await self._bot.send_media_group(job.chat_id, media=media)
                    await self._history.add(
                        job.user_id,
                        "stickers",
                        "Стикер-пак",
                        image_file_id=job.photo_file_id,
                        meta={"count": len(stickers)},
                    )
                    await self._bot.send_message(
                        job.chat_id,
                        f"Готово! {len(stickers)} стикера в формате WebP 512×512.\n"
                        "Их можно добавить в Telegram через @Stickers бота.",
                    )
            except asyncio.TimeoutError:
                await self.safe_edit(job.chat_id, job.status_message_id, "Таймаут.")
            except ReplicateModelFailed as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка:\n{exc}")
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Replicate:\n{exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("Sticker error")
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка: {exc}")

    async def _to_sticker(self, input_path: Path, output_path: Path) -> None:
        no_bg = input_path.with_suffix(".nobg.png")
        try:
            url = await self._replicate.run(
                self._settings.remove_bg_model,
                {"image": input_path},
            )
            await self._io.download_url(url, no_bg)
            src = no_bg
        except Exception:  # noqa: BLE001
            src = input_path

        cmd = [
            "ffmpeg", "-y", "-i", str(src),
            "-vf",
            "scale=512:512:force_original_aspect_ratio=decrease,"
            "pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000",
            "-c:v", "libwebp", "-quality", "90",
            str(output_path),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore")[-300:])
