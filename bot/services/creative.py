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
from bot.creative_catalog import ICONIC_LOCATIONS, IMPOSSIBLE_SCENES
from bot.services.history import HistoryStore
from bot.services.media import ReplicateModelFailed, ReplicateService, TelegramIO
from bot.services.pricing import estimate_restore, estimate_scene

log = logging.getLogger(__name__)


@dataclass(slots=True)
class CreativeJob:
    chat_id: int
    user_id: int
    status_message_id: int
    kind: str
    photo_file_id: str
    mode: str = "restore"
    scene_key: str = "eiffel"
    scene_type: str = "iconic"


class CreativeService:
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

    async def run(self, job: CreativeJob) -> None:
        async with self._semaphore:
            try:
                with tempfile.TemporaryDirectory(prefix="creative_") as tmp_str:
                    tmp = Path(tmp_str)
                    image = tmp / "input.jpg"
                    await self._io.download_file(job.photo_file_id, image)

                    if job.kind == "restore":
                        await self._run_restore(job, image, tmp)
                    else:
                        await self._run_scene(job, image, tmp)
            except asyncio.TimeoutError:
                await self.safe_edit(
                    job.chat_id, job.status_message_id,
                    "Генерация заняла слишком много времени.",
                )
            except ReplicateModelFailed as exc:
                await self.safe_edit(
                    job.chat_id, job.status_message_id, f"Ошибка модели:\n{exc}",
                )
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(
                    job.chat_id, job.status_message_id, f"Replicate:\n{exc}",
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Creative error")
                await self.safe_edit(
                    job.chat_id, job.status_message_id, f"Ошибка: {exc}",
                )

    async def _run_restore(self, job: CreativeJob, image: Path, tmp: Path) -> None:
        await self.safe_edit(job.chat_id, job.status_message_id, "Восстанавливаю фото...")
        current = image
        if job.mode in ("restore", "both"):
            restored = tmp / "restored.png"
            url = await asyncio.wait_for(
                self._replicate.run(
                    self._settings.restore_model,
                    {"input_image": current},
                ),
                timeout=self._settings.creative_timeout_seconds,
            )
            await self._io.download_url(url, restored)
            current = restored

        if job.mode in ("upscale", "both"):
            await self.safe_edit(job.chat_id, job.status_message_id, "Улучшаю детали и апскейл...")
            upscaled = tmp / "upscaled.png"
            url = await asyncio.wait_for(
                self._replicate.run(
                    self._settings.upscale_model,
                    {"image": current, "scale": 2, "face_enhance": True},
                ),
                timeout=self._settings.creative_timeout_seconds,
            )
            await self._io.download_url(url, upscaled)
            current = upscaled

        sent = await self._bot.send_photo(
            job.chat_id,
            photo=FSInputFile(current),
            caption="Готово 🖼",
        )
        photo_id = sent.photo[-1].file_id
        item = await self._history.add(
            job.user_id, "restore", "Реставрация фото",
            image_file_id=photo_id,
            meta={"mode": job.mode},
        )
        from bot.keyboards import image_pipeline_keyboard
        await self._bot.send_message(
            job.chat_id,
            estimate_restore(upscale=job.mode != "restore").format_message(),
            reply_markup=image_pipeline_keyboard(item.id),
        )

    async def _run_scene(self, job: CreativeJob, image: Path, tmp: Path) -> None:
        await self.safe_edit(job.chat_id, job.status_message_id, "Создаю сцену...")
        if job.scene_type == "impossible":
            preset = IMPOSSIBLE_SCENES.get(job.scene_key, IMPOSSIBLE_SCENES["random"])
            model = self._settings.impossible_scene_model
            inputs = {
                "input_image": image,
                "impossible_scenario": preset.value,
                "gender": "none",
                "aspect_ratio": "match_input_image",
            }
            title = f"Мем: {preset.label_ru}"
        else:
            preset = ICONIC_LOCATIONS.get(job.scene_key, ICONIC_LOCATIONS["random"])
            model = self._settings.iconic_scene_model
            inputs = {
                "input_image": image,
                "iconic_location": preset.value,
                "gender": "none",
                "aspect_ratio": "match_input_image",
            }
            title = f"Сцена: {preset.label_ru}"

        url = await asyncio.wait_for(
            self._replicate.run(model, inputs),
            timeout=self._settings.creative_timeout_seconds,
        )
        result = tmp / "scene.png"
        await self._io.download_url(url, result)
        sent = await self._bot.send_photo(job.chat_id, photo=FSInputFile(result), caption="Готово 🌍")
        photo_id = sent.photo[-1].file_id
        item = await self._history.add(
            job.user_id, "scene", title,
            image_file_id=photo_id,
            meta={"scene_type": job.scene_type, "scene_key": job.scene_key},
        )
        from bot.keyboards import image_pipeline_keyboard
        await self._bot.send_message(
            job.chat_id,
            estimate_scene(job.scene_type).format_message(),
            reply_markup=image_pipeline_keyboard(item.id),
        )
