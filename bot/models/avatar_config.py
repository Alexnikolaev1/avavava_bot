from __future__ import annotations

from dataclasses import asdict, dataclass

from bot.catalog import ANIMALS, EMOTIONS, GENDERS, STYLES, build_avatar_prompt


@dataclass(slots=True)
class AvatarConfig:
    animal_key: str | None = None
    custom_animal: str | None = None
    style_key: str = "cartoon"
    gender_key: str = "neutral"
    emotion_key: str = "happy"
    source: str = "generated"

    def animal_description(self) -> str:
        if self.custom_animal:
            return self.custom_animal
        meta = ANIMALS.get(self.animal_key or "cat", ANIMALS["cat"])
        return meta.prompt_en

    def to_prompt(self) -> str:
        return build_avatar_prompt(
            self.animal_description(),
            self.style_key,
            self.gender_key,
            self.emotion_key,
        )

    def auto_name(self) -> str:
        if self.custom_animal:
            subject = self.custom_animal[:28]
        else:
            meta = ANIMALS.get(self.animal_key or "cat", ANIMALS["cat"])
            subject = meta.label_ru
        style = STYLES.get(self.style_key, STYLES["cartoon"]).label_ru
        emotion = EMOTIONS.get(self.emotion_key, EMOTIONS["happy"]).label_ru
        gender = GENDERS.get(self.gender_key, GENDERS["neutral"])
        if gender.key == "neutral":
            return f"{subject} · {style} · {emotion}"
        return f"{subject} · {gender.label_ru} · {style} · {emotion}"

    def summary(self) -> str:
        style = STYLES.get(self.style_key, STYLES["cartoon"])
        emotion = EMOTIONS.get(self.emotion_key, EMOTIONS["happy"])
        gender = GENDERS.get(self.gender_key, GENDERS["neutral"])
        if self.custom_animal:
            who = self.custom_animal
        else:
            meta = ANIMALS.get(self.animal_key or "cat", ANIMALS["cat"])
            who = f"{meta.emoji} {meta.label_ru}"
        parts = [who, f"{style.emoji} {style.label_ru}", f"{emotion.emoji} {emotion.label_ru}"]
        if gender.key != "neutral":
            parts.insert(1, f"{gender.emoji} {gender.label_ru}")
        return " · ".join(parts)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> AvatarConfig:
        return cls(
            animal_key=data.get("animal_key"),
            custom_animal=data.get("custom_animal"),
            style_key=data.get("style_key", "cartoon"),
            gender_key=data.get("gender_key", "neutral"),
            emotion_key=data.get("emotion_key", "happy"),
            source=data.get("source", "generated"),
        )

    @classmethod
    def from_fsm(cls, data: dict) -> AvatarConfig:
        return cls(
            animal_key=data.get("animal_key"),
            custom_animal=data.get("custom_animal"),
            style_key=data.get("style_key", "cartoon"),
            gender_key=data.get("gender_key", "neutral"),
            emotion_key=data.get("emotion_key", "happy"),
            source=data.get("source", "generated"),
        )
