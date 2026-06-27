from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CostEstimate:
    label: str
    usd_low: float
    usd_high: float

    def format_short(self) -> str:
        if abs(self.usd_low - self.usd_high) < 0.01:
            return f"~${self.usd_low:.2f}"
        return f"~${self.usd_low:.2f}–${self.usd_high:.2f}"

    def format_message(self) -> str:
        return f"<b>{self.label}</b>: {self.format_short()}"


def estimate_avatar() -> CostEstimate:
    return CostEstimate("Рисование персонажа", 0.003, 0.02)


def estimate_lipsync(seconds: int, *, kling: bool = False) -> CostEstimate:
    if kling:
        cost = max(0.35, seconds * 0.075)
        return CostEstimate("Kling Avatar (lip-sync)", cost * 0.9, cost * 1.1)
    cost = max(0.08, seconds * 0.015)
    return CostEstimate("SadTalker (lip-sync)", cost * 0.8, cost * 1.2)


def estimate_photoshoot(preset: str) -> CostEstimate:
    if preset == "official":
        return CostEstimate("Headshot", 0.03, 0.08)
    if preset == "art":
        return CostEstimate("Художественные стили", 0.008, 0.02)
    return CostEstimate("PhotoMaker", 0.02, 0.06)


def estimate_motion(mode: str, seconds: int, *, kling_mode: str = "std") -> CostEstimate:
    if mode == "replace":
        rate = 0.08 if seconds <= 10 else 0.12
        cost = seconds * rate
        return CostEstimate("Wan Animate Replace", cost * 0.8, cost * 1.3)
    rate = 0.14 if kling_mode == "std" else 0.18
    cost = seconds * rate
    return CostEstimate("Kling Motion Control", cost * 0.95, cost * 1.05)


def estimate_i2v(seconds: int, *, mode: str = "standard") -> CostEstimate:
    base = 0.25 if mode == "standard" else 0.45
    mult = seconds / 5
    return CostEstimate("Видео по промпту", base * mult * 0.8, base * mult * 1.2)


def estimate_voice_tts() -> CostEstimate:
    return CostEstimate("Клон голоса (XTTS)", 0.03, 0.06)


def estimate_restore(*, upscale: bool = False) -> CostEstimate:
    if upscale:
        return CostEstimate("Реставрация + апскейл", 0.02, 0.06)
    return CostEstimate("Реставрация фото", 0.01, 0.04)


def estimate_scene(kind: str) -> CostEstimate:
    label = "Сцена (мем)" if kind == "impossible" else "Сцена (локация)"
    return CostEstimate(label, 0.03, 0.08)


def estimate_singing(seconds: int) -> CostEstimate:
    cost = max(0.35, seconds * 0.075)
    return CostEstimate("Поющий аватар", cost * 0.9, cost * 1.1)


def estimate_stickers(count: int = 4) -> CostEstimate:
    return CostEstimate("Стикер-пак", 0.02 * count, 0.05 * count)


def estimate_subtitles() -> CostEstimate:
    return CostEstimate("Субтитры (Whisper)", 0.01, 0.03)
