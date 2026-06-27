from __future__ import annotations

import asyncio
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import replicate
from aiogram import Bot
from aiogram.types import FSInputFile

from bot.config import Settings
from bot.services.history import HistoryStore
from bot.services.media import ReplicateModelFailed, ReplicateService, TelegramIO, compress_for_telegram

log = logging.getLogger(__name__)


@dataclass(slots=True)
class SubtitlesJob:
    chat_id: int
    user_id: int
    status_message_id: int
    video_file_id: str


class SubtitlesService:
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

    async def run(self, job: SubtitlesJob) -> None:
        async with self._semaphore:
            try:
                await self.safe_edit(job.chat_id, job.status_message_id, "Распознаю речь...")
                with tempfile.TemporaryDirectory(prefix="subs_") as tmp_str:
                    tmp = Path(tmp_str)
                    video = tmp / "input.mp4"
                    audio = tmp / "audio.wav"
                    srt = tmp / "subs.srt"
                    output = tmp / "subtitled.mp4"
                    final = tmp / "final.mp4"

                    await self._io.download_file(job.video_file_id, video)
                    await self._extract_audio(video, audio)

                    result = await asyncio.wait_for(
                        self._replicate.run_raw(
                            self._settings.whisper_model,
                            {
                                "audio": audio,
                                "task": "transcribe",
                                "return_timestamps": True,
                            },
                        ),
                        timeout=self._settings.subtitles_timeout_seconds,
                    )
                    segments = self._parse_whisper_output(result)
                    if not segments:
                        await self.safe_edit(
                            job.chat_id, job.status_message_id,
                            "Речь не распознана. Попробуй другое видео.",
                        )
                        return

                    await self.safe_edit(job.chat_id, job.status_message_id, "Накладываю субтитры...")
                    self._write_srt(segments, srt)
                    await self._burn_subtitles(video, srt, output)
                    await compress_for_telegram(output, final)

                    sent = await self._bot.send_video(
                        job.chat_id,
                        video=FSInputFile(final),
                        caption="Готово 📝",
                        supports_streaming=True,
                    )
                    await self._history.add(
                        job.user_id,
                        "subtitles",
                        "Видео с субтитрами",
                        video_file_id=sent.video.file_id,
                        meta={"segments": len(segments)},
                    )
            except asyncio.TimeoutError:
                await self.safe_edit(job.chat_id, job.status_message_id, "Таймаут.")
            except ReplicateModelFailed as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка:\n{exc}")
            except replicate.exceptions.ReplicateError as exc:
                await self.safe_edit(job.chat_id, job.status_message_id, f"Replicate:\n{exc}")
            except Exception as exc:  # noqa: BLE001
                log.exception("Subtitles error")
                await self.safe_edit(job.chat_id, job.status_message_id, f"Ошибка: {exc}")

    @staticmethod
    async def _extract_audio(video: Path, audio: Path) -> None:
        cmd = [
            "ffmpeg", "-y", "-i", str(video),
            "-vn", "-ar", "16000", "-ac", "1",
            "-c:a", "pcm_s16le", str(audio),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

    @staticmethod
    def _parse_whisper_output(output: object) -> list[tuple[float, float, str]]:
        if isinstance(output, dict):
            chunks = output.get("chunks") or output.get("segments") or []
            result: list[tuple[float, float, str]] = []
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                text = str(chunk.get("text", "")).strip()
                ts = chunk.get("timestamp") or chunk.get("timestamps")
                if isinstance(ts, (list, tuple)) and len(ts) >= 2:
                    start, end = float(ts[0]), float(ts[1])
                else:
                    start = float(chunk.get("start", 0))
                    end = float(chunk.get("end", start + 2))
                if text:
                    result.append((start, end, text))
            if result:
                return result
            plain = str(output.get("text", "")).strip()
            if plain:
                return [(0.0, 5.0, plain)]
        if isinstance(output, str) and output.strip():
            return [(0.0, 5.0, output.strip())]
        return []

    @staticmethod
    def _write_srt(segments: list[tuple[float, float, str]], path: Path) -> None:
        lines: list[str] = []
        for idx, (start, end, text) in enumerate(segments, 1):
            lines.append(str(idx))
            lines.append(
                f"{SubtitlesService._ts(start)} --> {SubtitlesService._ts(end)}"
            )
            lines.append(text)
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def _ts(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    @staticmethod
    async def _burn_subtitles(video: Path, srt: Path, output: Path) -> None:
        safe_srt = str(srt).replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-i", str(video),
            "-vf", f"subtitles='{safe_srt}':force_style='FontSize=18,PrimaryColour=&HFFFFFF&'",
            "-c:a", "copy",
            str(output),
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode(errors="ignore")[-400:])
