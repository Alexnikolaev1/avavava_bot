from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PhotoshootPreset:
    key: str
    label_ru: str
    emoji: str
    description: str
    max_photos: int


PRESETS: dict[str, PhotoshootPreset] = {
    "official": PhotoshootPreset(
        "official",
        "Официальное фото",
        "👔",
        "Студийный headshot для резюме и соцсетей",
        1,
    ),
    "art": PhotoshootPreset(
        "art",
        "Художественные стили",
        "🎨",
        "3D, pixel art, claymation и другие",
        1,
    ),
    "custom": PhotoshootPreset(
        "custom",
        "Свой промпт",
        "✨",
        "1–4 фото + текст — максимальное сходство лица",
        4,
    ),
}

HEADSHOT_BACKGROUNDS: dict[str, str] = {
    "neutral": "🤍 Нейтральный",
    "office": "🏢 Офис",
    "gray": "⬜ Серый фон",
}

HEADSHOT_GENDERS: dict[str, str] = {
    "male": "♂️ Мужской",
    "female": "♀️ Женский",
}

# Значения поля style для fofr/face-to-many
FACE_TO_MANY_STYLES: dict[str, tuple[str, str]] = {
    "3d": ("3D", "3D render portrait"),
    "pixel": ("Pixel art", "pixel art game character portrait"),
    "clay": ("Claymation", "claymation stop motion character"),
    "toy": ("Toy", "cute toy figurine portrait"),
    "emoji": ("Emoji", "emoji style avatar portrait"),
    "game": ("Video game", "video game character portrait"),
}

# style_name для PhotoMaker
PHOTOMAKER_STYLES: dict[str, str] = {
    "photo": "Photographic (Default)",
    "cinematic": "Cinematic",
    "digital": "Digital Art",
    "fantasy": "Fantasy art",
    "neon": "Neonpunk",
    "comic": "Comic book",
    "line": "Line art",
    "disney": "Disney Charactor",
}

CUSTOM_PROMPT_HINTS = (
    "Примеры промпта (PhotoMaker):\n"
    "• <i>a photo of a man img, cyberpunk warrior, neon city</i>\n"
    "• <i>a photo of a woman img, oil painting, renaissance portrait</i>\n\n"
    "Слово <code>img</code> обязательно — это триггер модели."
)
