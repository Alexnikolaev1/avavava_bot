from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnimalMeta:
    key: str
    label_ru: str
    emoji: str
    prompt_en: str


@dataclass(frozen=True, slots=True)
class StyleMeta:
    key: str
    label_ru: str
    emoji: str
    prompt_suffix: str


@dataclass(frozen=True, slots=True)
class GenderMeta:
    key: str
    label_ru: str
    emoji: str
    prompt_suffix: str


@dataclass(frozen=True, slots=True)
class EmotionMeta:
    key: str
    label_ru: str
    emoji: str
    prompt_suffix: str


ANIMALS: dict[str, AnimalMeta] = {
    "cat": AnimalMeta("cat", "Кот", "🐱", "cute cartoon cat"),
    "dog": AnimalMeta("dog", "Собака", "🐶", "friendly cartoon dog"),
    "fox": AnimalMeta("fox", "Лиса", "🦊", "clever cartoon fox"),
    "bear": AnimalMeta("bear", "Медведь", "🐻", "fluffy cartoon bear"),
    "rabbit": AnimalMeta("rabbit", "Кролик", "🐰", "adorable cartoon rabbit"),
    "panda": AnimalMeta("panda", "Панда", "🐼", "cute cartoon panda"),
    "lion": AnimalMeta("lion", "Лев", "🦁", "brave cartoon lion"),
    "frog": AnimalMeta("frog", "Лягушка", "🐸", "cheerful cartoon frog"),
    "owl": AnimalMeta("owl", "Сова", "🦉", "wise cartoon owl"),
    "penguin": AnimalMeta("penguin", "Пингвин", "🐧", "cute cartoon penguin"),
}

GENDERS: dict[str, GenderMeta] = {
    "neutral": GenderMeta("neutral", "Нейтральный", "⚪", ""),
    "male": GenderMeta(
        "male",
        "Мальчик",
        "♂️",
        "masculine boy character, slightly broader features, boyish charm",
    ),
    "female": GenderMeta(
        "female",
        "Девочка",
        "♀️",
        "feminine girl character, softer features, long eyelashes, cute",
    ),
}

STYLES: dict[str, StyleMeta] = {
    "cartoon": StyleMeta(
        "cartoon",
        "Классический мультфильм",
        "🎬",
        "classic 2D cartoon style, bold outlines, vibrant flat colors",
    ),
    "pixar": StyleMeta(
        "pixar",
        "3D Pixar",
        "✨",
        "3D Pixar-style render, soft lighting, expressive character design",
    ),
    "anime": StyleMeta(
        "anime",
        "Аниме",
        "🌸",
        "anime style illustration, clean linework, expressive eyes",
    ),
    "sticker": StyleMeta(
        "sticker",
        "Стикер",
        "🏷",
        "cute sticker art style, thick outline, simple shading, emoji-like",
    ),
    "watercolor": StyleMeta(
        "watercolor",
        "Акварель",
        "🎨",
        "soft watercolor illustration, gentle textures, storybook feel",
    ),
}

EMOTIONS: dict[str, EmotionMeta] = {
    "happy": EmotionMeta(
        "happy",
        "Радость",
        "😊",
        "happy cheerful expression, warm smile, bright eyes",
    ),
    "excited": EmotionMeta(
        "excited",
        "Восторг",
        "🤩",
        "excited enthusiastic expression, sparkling eyes, big smile",
    ),
    "cool": EmotionMeta(
        "cool",
        "Крутость",
        "😎",
        "cool confident expression, relaxed smirk, self-assured look",
    ),
    "shy": EmotionMeta(
        "shy",
        "Смущение",
        "😳",
        "shy bashful expression, blushing cheeks, gentle smile",
    ),
    "surprised": EmotionMeta(
        "surprised",
        "Удивление",
        "😲",
        "surprised expression, wide open eyes, slightly open mouth",
    ),
    "sad": EmotionMeta(
        "sad",
        "Грусть",
        "😢",
        "sad melancholic expression, teary eyes, downturned mouth",
    ),
    "angry": EmotionMeta(
        "angry",
        "Злость",
        "😠",
        "angry fierce expression, furrowed brows, determined look",
    ),
    "thinking": EmotionMeta(
        "thinking",
        "Задумчивость",
        "🤔",
        "thoughtful curious expression, one raised eyebrow, pensive look",
    ),
}

PORTRAIT_SUFFIX = (
    "portrait headshot, front-facing, shoulders visible, "
    "large expressive eyes, clearly visible mouth and nose, "
    "symmetrical face, centered composition, "
    "plain soft gradient background, no text, no watermark, "
    "high quality character design, suitable for facial animation"
)


def build_avatar_prompt(
    animal_description: str,
    style_key: str,
    gender_key: str = "neutral",
    emotion_key: str = "happy",
) -> str:
    style = STYLES.get(style_key, STYLES["cartoon"])
    gender = GENDERS.get(gender_key, GENDERS["neutral"])
    emotion = EMOTIONS.get(emotion_key, EMOTIONS["happy"])

    parts = [animal_description]
    if gender.prompt_suffix:
        parts.append(gender.prompt_suffix)
    parts.append(emotion.prompt_suffix)
    parts.append(style.prompt_suffix)
    parts.append(PORTRAIT_SUFFIX)
    return ", ".join(parts)
