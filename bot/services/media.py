from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiohttp
import replicate
from aiogram import Bot

from bot.config import Settings

log = logging.getLogger(__name__)


class TelegramIO:
    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def download_file(self, file_id: str, destination: Path) -> None:
        tg_file = await self._bot.get_file(file_id)
        await self._bot.download_file(tg_file.file_path, destination=destination)

    async def download_url(self, url: str, destination: Path) -> None:
        await download_url(url, destination)


class ReplicateService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = replicate.Client(api_token=settings.replicate_api_token)

    async def run(self, model: str, inputs: dict[str, Any]) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_blocking, model, inputs)

    def _run_blocking(self, model: str, inputs: dict[str, Any]) -> str:
        opened: list[Any] = []
        prepared: dict[str, Any] = {}
        try:
            for key, value in inputs.items():
                if isinstance(value, Path):
                    handle = open(value, "rb")
                    opened.append(handle)
                    prepared[key] = handle
                else:
                    prepared[key] = value
            output = self._client.run(model, input=prepared)
            return self._extract_url(output)
        finally:
            for handle in opened:
                handle.close()

    @staticmethod
    def _extract_url(output: Any) -> str:
        if isinstance(output, list) and output:
            return ReplicateService._extract_url(output[0])
        if hasattr(output, "url"):
            return str(output.url)
        return str(output)


async def download_url(url: str, destination: Path) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            with open(destination, "wb") as handle:
                async for chunk in resp.content.iter_chunked(1024 * 256):
                    handle.write(chunk)


class AvatarGenerator:
    def __init__(self, replicate: ReplicateService, settings: Settings) -> None:
        self._replicate = replicate
        self._settings = settings

    async def generate(self, prompt: str, output_path: Path) -> Path:
        log.info("Generating avatar with model=%s", self._settings.avatar_model)
        url = await self._replicate.run(
            self._settings.avatar_model,
            {
                "prompt": prompt,
                "num_outputs": 1,
                "aspect_ratio": "1:1",
                "output_format": "png",
                "output_quality": 90,
            },
        )
        await download_url(url, output_path)
        await prepare_avatar_image(output_path)
        return output_path


class SadTalkerService:
    def __init__(self, replicate: ReplicateService, settings: Settings) -> None:
        self._replicate = replicate
        self._settings = settings

    async def animate(
        self,
        image_path: Path,
        audio_path: Path,
        *,
        cartoon: bool = True,
    ) -> str:
        log.info(
            "Running SadTalker model=%s cartoon=%s",
            self._settings.sadtalker_model,
            cartoon,
        )
        if cartoon:
            inputs = {
                "source_image": image_path,
                "driven_audio": audio_path,
                "enhancer": None,
                "preprocess": "crop",
                "still": True,
                "face_model_resolution": "256",
            }
        else:
            inputs = {
                "source_image": image_path,
                "driven_audio": audio_path,
                "enhancer": "gfpgan",
                "preprocess": "full",
                "still": True,
            }
        return await self._replicate.run(self._settings.sadtalker_model, inputs)


async def prepare_avatar_image(path: Path, size: int = 512) -> None:
    """Нормализует PNG/JPEG под SadTalker: квадрат, чёткие края."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-vf",
        f"scale={size}:{size}:force_original_aspect_ratio=decrease,"
        f"pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=0xE8E8E8",
        "-frames:v",
        "1",
        str(path.with_suffix(".prepared.png")),
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        log.warning(
            "Avatar prepare skipped: %s",
            stderr.decode(errors="ignore")[-300:],
        )
        return
    prepared = path.with_suffix(".prepared.png")
    prepared.replace(path)


async def compress_for_telegram(
    input_path: Path,
    output_path: Path,
    *,
    crf: int = 28,
    scale_height: int | None = None,
) -> None:
    scale_filter: list[str] = []
    if scale_height:
        scale_filter = ["-vf", f"scale=-2:{scale_height}"]

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        *scale_filter,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(crf),
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            f"ffmpeg завершился с ошибкой: {stderr.decode(errors='ignore')[-500:]}"
        )
