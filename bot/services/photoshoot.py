from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import replicate
from aiogram import Bot
from aiogram.types import FSInputFile, InputMediaPhoto

from bot.config import Settings
from bot.photoshoot_catalog import FACE_TO_MANY_STYLES, PHOTOMAKER_STYLES
from bot.services.media import ReplicateModelFailed, ReplicateService, TelegramIO

log = logging.getLogger(__name__)


@dataclass(slots=True)
class PhotoshootJob:
    chat_id: int
    status_message_id: int
    preset: str
    photo_file_ids: list[str]
    gender: str | None = None
    background: str = "neutral"
    ftm_style_key: str = "3d"
    pm_style_key: str = "photo"
    custom_prompt: str | None = None


class PhotoshootService:
    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        replicate: ReplicateService,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._bot = bot
        self._settings = settings
        self._replicate = replicate
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

    async def run(self, job: PhotoshootJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Скачиваю фото и отправляю в нейросеть...",
                )
                with tempfile.TemporaryDirectory(prefix="photoshoot_") as tmp_str:
                    tmp = Path(tmp_str)
                    paths = await self._download_photos(job.photo_file_ids, tmp)

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        self._status_for_preset(job.preset),
                    )

                    urls = await asyncio.wait_for(
                        self._generate(job, paths),
                        timeout=self._settings.photoshoot_timeout_seconds,
                    )

                    await self.safe_edit(
                        job.chat_id,
                        job.status_message_id,
                        f"Готово! Отправляю {len(urls)} фото...",
                    )
                    await self._send_results(job.chat_id, urls, tmp)
            except asyncio.TimeoutError:
                log.exception("Photoshoot timed out chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    "Генерация заняла слишком много времени. Попробуй ещё раз.",
                )
            except ReplicateModelFailed as exc:
                log.exception("Photoshoot model failed chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Не удалось создать фотосессию:\n{exc}",
                )
            except replicate.exceptions.ReplicateError as exc:
                log.exception("Photoshoot replicate error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Replicate вернул ошибку:\n{exc}",
                )
            except Exception as exc:  # noqa: BLE001
                log.exception("Photoshoot error chat_id=%s", job.chat_id)
                await self.safe_edit(
                    job.chat_id,
                    job.status_message_id,
                    f"Ошибка фотосессии: {exc}",
                )

    async def _download_photos(self, file_ids: list[str], tmp: Path) -> list[Path]:
        paths: list[Path] = []
        for idx, file_id in enumerate(file_ids):
            path = tmp / f"face_{idx}.jpg"
            await self._io.download_file(file_id, path)
            paths.append(path)
        return paths

    async def _generate(self, job: PhotoshootJob, paths: list[Path]) -> list[str]:
        if job.preset == "official":
            return await self._official(job, paths[0])
        if job.preset == "art":
            return await self._art(job, paths[0])
        return await self._custom(job, paths)

    async def _official(self, job: PhotoshootJob, image: Path) -> list[str]:
        inputs: dict[str, Any] = {
            "input_image": image,
            "background": job.background,
            "aspect_ratio": "1:1",
            "output_format": "png",
        }
        if job.gender:
            inputs["gender"] = job.gender
        log.info("Photoshoot official model=%s", self._settings.photoshoot_headshot_model)
        url = await self._replicate.run(self._settings.photoshoot_headshot_model, inputs)
        return [url]

    async def _art(self, job: PhotoshootJob, image: Path) -> list[str]:
        style_value, prompt_suffix = FACE_TO_MANY_STYLES.get(
            job.ftm_style_key,
            FACE_TO_MANY_STYLES["3d"],
        )
        log.info(
            "Photoshoot art model=%s style=%s",
            self._settings.photoshoot_style_model,
            style_value,
        )
        return await self._replicate.run_many(
            self._settings.photoshoot_style_model,
            {
                "image": image,
                "style": style_value,
                "prompt": f"a person, {prompt_suffix}, portrait, high quality",
                "instant_id_strength": 0.85,
                "denoising_strength": 0.65,
            },
        )

    async def _custom(self, job: PhotoshootJob, paths: list[Path]) -> list[str]:
        style_name = PHOTOMAKER_STYLES.get(
            job.pm_style_key,
            PHOTOMAKER_STYLES["photo"],
        )
        prompt = job.custom_prompt or "a photo of a person img, professional portrait"
        if "img" not in prompt:
            prompt = f"{prompt} img"

        inputs: dict[str, Any] = {
            "first_image": paths[0],
            "prompt": prompt,
            "style_name": style_name,
            "num_outputs": min(4, max(1, len(paths) + 1)),
            "num_steps": 30,
            "style_strength_ratio": 20,
            "guidance_scale": 5,
        }
        image_keys = ("second_image", "third_image", "fourth_image")
        for path, key in zip(paths[1:], image_keys, strict=False):
            inputs[key] = path

        log.info("Photoshoot custom model=%s style=%s", self._settings.photoshoot_custom_model, style_name)
        return await self._replicate.run_many(
            self._settings.photoshoot_custom_model,
            inputs,
        )

    @staticmethod
    def _status_for_preset(preset: str) -> str:
        return {
            "official": "Делаю официальный headshot...",
            "art": "Рисую художественные портреты...",
            "custom": "Генерирую фото по твоему промпту...",
        }.get(preset, "Генерирую фото...")

    async def _send_results(self, chat_id: int, urls: list[str], tmp: Path) -> None:
        local_paths: list[Path] = []
        for idx, url in enumerate(urls[:10]):
            path = tmp / f"result_{idx}.png"
            await self._io.download_url(url, path)
            local_paths.append(path)

        if not local_paths:
            await self._bot.send_message(chat_id, "Модель не вернула изображений.")
            return

        if len(local_paths) == 1:
            await self._bot.send_photo(
                chat_id=chat_id,
                photo=FSInputFile(local_paths[0]),
                caption="Готово 📸",
            )
            return

        media = [
            InputMediaPhoto(media=FSInputFile(path))
            for path in local_paths[:10]
        ]
        await self._bot.send_media_group(chat_id=chat_id, media=media)
        await self._bot.send_message(chat_id, f"Готово 📸 — {len(local_paths)} варианта")
