from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import aiohttp
import replicate
from aiogram import Bot
from replicate.exceptions import ModelError

from bot.config import Settings

log = logging.getLogger(__name__)

LANDMARK_ERROR_MARKERS = (
    "can not detect the landmark",
    "cannot detect the landmark",
    "no face detected",
)


def is_landmark_failure(exc: ReplicateModelFailed) -> bool:
    combined = f"{exc}\n{exc.logs or ''}".lower()
    return any(marker in combined for marker in LANDMARK_ERROR_MARKERS)


def parse_replicate_failure(error: Any, logs: str) -> str:
    """Достаёт реальную причину из logs — SadTalker иногда кладёт мусор в error."""
    if logs:
        for line in reversed(logs.splitlines()):
            cleaned = line.strip()
            lower = cleaned.lower()
            if "can not detect the landmark" in lower:
                return "can not detect the landmark from source image"
            if "no face" in lower and "detect" in lower:
                return cleaned
            if cleaned.startswith("raise ") and ("'" in cleaned or '"' in cleaned):
                for quote in ("'", '"'):
                    if quote in cleaned:
                        parts = cleaned.split(quote)
                        if len(parts) >= 2 and parts[1]:
                            return parts[1]

    if isinstance(error, str) and "exceptions must derive from baseexception" not in error.lower():
        return error
    if logs and any(marker in logs.lower() for marker in LANDMARK_ERROR_MARKERS):
        return "can not detect the landmark from source image"
    if isinstance(error, str):
        return error
    return "модель завершилась с ошибкой"


class ReplicateModelFailed(RuntimeError):
    """SadTalker/Flux вернули failed prediction с понятным текстом."""

    def __init__(self, message: str, *, logs: str | None = None) -> None:
        super().__init__(message)
        self.logs = logs


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

    async def run_many(self, model: str, inputs: dict[str, Any]) -> list[str]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_many_blocking, model, inputs)

    async def run_raw(self, model: str, inputs: dict[str, Any]) -> Any:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._run_raw_blocking, model, inputs)

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
            try:
                output = self._client.run(model, input=prepared)
            except ModelError as exc:
                raise self._model_error(exc) from exc
            return self._extract_url(output)
        finally:
            for handle in opened:
                handle.close()

    def _run_many_blocking(self, model: str, inputs: dict[str, Any]) -> list[str]:
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
            try:
                output = self._client.run(model, input=prepared)
            except ModelError as exc:
                raise self._model_error(exc) from exc
            return self._extract_urls(output)
        finally:
            for handle in opened:
                handle.close()

    def _run_raw_blocking(self, model: str, inputs: dict[str, Any]) -> Any:
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
            try:
                return self._client.run(model, input=prepared)
            except ModelError as exc:
                raise self._model_error(exc) from exc
        finally:
            for handle in opened:
                handle.close()

    @staticmethod
    def _model_error(exc: ModelError) -> ReplicateModelFailed:
        logs = exc.prediction.logs or ""
        message = parse_replicate_failure(exc.prediction.error, logs)
        log.error(
            "Replicate model failed: %s | prediction=%s | logs_tail=%s",
            message,
            exc.prediction.id,
            logs[-800:],
        )
        return ReplicateModelFailed(message, logs=logs)

    @staticmethod
    def _extract_url(output: Any) -> str:
        if isinstance(output, list) and output:
            return ReplicateService._extract_url(output[0])
        if hasattr(output, "url"):
            return str(output.url)
        return str(output)

    @staticmethod
    def _extract_urls(output: Any) -> list[str]:
        if isinstance(output, list):
            urls = [ReplicateService._extract_url(item) for item in output if item is not None]
            return urls or [ReplicateService._extract_url(output)]
        return [ReplicateService._extract_url(output)]


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
        wav_path = audio_path.with_suffix(".wav")
        await convert_audio_to_wav(audio_path, wav_path)
        await prepare_face_image(image_path)

        model = self._settings.sadtalker_model
        inputs = self._build_inputs(model, image_path, wav_path, cartoon=cartoon)
        log.info("Running SadTalker model=%s cartoon=%s", model, cartoon)
        return await self._replicate.run(model, inputs)

    @staticmethod
    def _build_inputs(
        model: str,
        image_path: Path,
        audio_path: Path,
        *,
        cartoon: bool,
    ) -> dict[str, Any]:
        model_key = model.lower()
        if "cjwbw/sadtalker" in model_key:
            if cartoon:
                return {
                    "source_image": image_path,
                    "driven_audio": audio_path,
                    "use_enhancer": False,
                    "preprocess": "crop",
                    "still_mode": True,
                    "size_of_image": 256,
                }
            return {
                "source_image": image_path,
                "driven_audio": audio_path,
                "use_enhancer": True,
                "preprocess": "crop",
                "still_mode": True,
                "size_of_image": 256,
            }

        # lucataco/sadtalker: не передаём enhancer=None — это ломает cog-модель
        common = {
            "source_image": image_path,
            "driven_audio": audio_path,
            "preprocess": "crop",
            "still": True,
        }
        if not cartoon:
            common["enhancer"] = "gfpgan"
        return common


class KlingAvatarService:
    """Kling Avatar V2 — работает с людьми, мультяшками и животными-маскотами."""

    def __init__(self, replicate: ReplicateService, settings: Settings) -> None:
        self._replicate = replicate
        self._settings = settings

    async def animate(self, image_path: Path, audio_path: Path) -> str:
        mp3_path = audio_path.with_suffix(".kling.mp3")
        await convert_audio_for_kling(audio_path, mp3_path)

        model = self._settings.kling_avatar_model
        log.info("Running Kling Avatar model=%s mode=%s", model, self._settings.kling_avatar_mode)
        return await self._replicate.run(
            model,
            {
                "image": image_path,
                "audio": mp3_path,
                "mode": self._settings.kling_avatar_mode,
                "prompt": "character talking naturally to camera, expressive lip sync",
            },
        )


async def convert_audio_for_kling(input_path: Path, output_path: Path) -> None:
    """Kling принимает mp3/wav до 5 МБ."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "44100",
        "-ac",
        "1",
        "-b:a",
        "128k",
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
            f"ffmpeg audio convert failed: {stderr.decode(errors='ignore')[-500:]}"
        )


async def convert_audio_to_wav(input_path: Path, output_path: Path) -> None:
    """SadTalker принимает wav/mp4; Telegram voice приходит как ogg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
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
            f"ffmpeg audio convert failed: {stderr.decode(errors='ignore')[-500:]}"
        )


async def prepare_face_image(path: Path, size: int = 512) -> None:
    """Нормализует фото под SadTalker: квадратный JPEG, лицо по центру."""
    prepared = path.with_suffix(".prepared.jpg")
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-vf",
        f"scale={size}:{size}:force_original_aspect_ratio=decrease,"
        f"pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=0xE8E8E8",
        "-q:v",
        "2",
        str(prepared),
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        log.warning(
            "Face prepare skipped: %s",
            stderr.decode(errors="ignore")[-300:],
        )
        return
    prepared.replace(path)


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


async def get_media_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed: {stderr.decode(errors='ignore')[-300:]}"
        )
    return float(stdout.decode().strip())


async def prepare_reference_video(
    input_path: Path,
    output_path: Path,
    *,
    max_seconds: int,
    max_height: int = 720,
) -> float:
    """Обрезает и нормализует референс-видео под motion control."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-t",
        str(max_seconds),
        "-vf",
        f"scale=-2:{max_height}",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
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
            f"ffmpeg video prepare failed: {stderr.decode(errors='ignore')[-500:]}"
        )
    return await get_media_duration(output_path)
