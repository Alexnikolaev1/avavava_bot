from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MotionMode:
    key: str
    label_ru: str
    emoji: str
    description: str


MODES: dict[str, MotionMode] = {
    "replace": MotionMode(
        "replace",
        "В том же видео",
        "🎬",
        "Подменяет человека в ролике — фон и камера остаются",
    ),
    "kling": MotionMode(
        "kling",
        "Перенести движение",
        "💃",
        "Твой персонаж повторяет танец (Kling, подходит и для маскотов)",
    ),
}
