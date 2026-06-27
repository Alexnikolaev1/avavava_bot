from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScenePreset:
    key: str
    label_ru: str
    value: str


RESTORE_MODES: dict[str, tuple[str, str]] = {
    "restore": ("🩹 Реставрация", "Восстановить царапины и выцветание"),
    "upscale": ("🔍 Апскейл ×2", "Увеличить и улучшить лицо"),
    "both": ("✨ Реставрация + апскейл", "Полное восстановление"),
}

ICONIC_LOCATIONS: dict[str, ScenePreset] = {
    "eiffel": ScenePreset("eiffel", "🗼 Эйфелева башня", "Eiffel Tower"),
    "times": ScenePreset("times", "🌃 Times Square", "Times Square"),
    "taj": ScenePreset("taj", "🕌 Тадж-Махал", "Taj Mahal"),
    "colosseum": ScenePreset("colosseum", "🏛 Колизей", "Colosseum"),
    "random": ScenePreset("random", "🎲 Случайная локация", "Random"),
}

IMPOSSIBLE_SCENES: dict[str, ScenePreset] = {
    "space": ScenePreset("space", "🚀 Космос", "Floating in space as an astronaut"),
    "skydive": ScenePreset("skydive", "🪂 Скайдайв", "Skydiving from 30,000 feet"),
    "shark": ScenePreset("shark", "🦈 С акулами", "Swimming with great white sharks"),
    "mars": ScenePreset("mars", "🔴 Марс", "Walking on Mars surface"),
    "random": ScenePreset("random", "🎲 Случайный мем", "Random"),
}

I2V_DURATIONS: dict[str, int] = {"5": 5, "10": 10}

VOICE_LANGUAGES: dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "en": "🇺🇸 English",
    "es": "🇪🇸 Español",
    "de": "🇩🇪 Deutsch",
}
