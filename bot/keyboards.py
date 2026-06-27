from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.catalog import ANIMALS, EMOTIONS, GENDERS, STYLES
from bot.motion_catalog import MODES
from bot.creative_catalog import ICONIC_LOCATIONS, IMPOSSIBLE_SCENES, RESTORE_MODES, VOICE_LANGUAGES
from bot.photoshoot_catalog import (
    FACE_TO_MANY_STYLES,
    HEADSHOT_BACKGROUNDS,
    HEADSHOT_GENDERS,
    PHOTOMAKER_STYLES,
    PRESETS,
)

CB_ANIMAL = "animal:"
CB_GENDER = "gender:"
CB_STYLE = "style:"
CB_EMOTION = "emotion:"
CB_GENERATE = "action:generate"
CB_USE_PHOTO = "action:photo"
CB_REGENERATE = "action:regenerate"
CB_RESTART = "action:restart"
CB_FAV_SAVE = "fav:save"
CB_FAV_LIST = "fav:list"
CB_FAV_USE = "fav:use:"
CB_FAV_DEL = "fav:del:"
CB_FAV_NAME_AUTO = "fav:name:auto"
CB_PHOTO_MODE = "action:photo_mode"
CB_MASCOT_MODE = "action:mascot_mode"
CB_PHOTOSHOOT = "action:photoshoot"
CB_PS_PRESET = "ps:preset:"
CB_PS_BG = "ps:bg:"
CB_PS_GENDER = "ps:gender:"
CB_PS_FTM = "ps:ftm:"
CB_PS_PM = "ps:pm:"
CB_PS_PHOTOS_DONE = "ps:done"
CB_PS_DEFAULT_PROMPT = "ps:defprompt"
CB_PS_RESTART = "ps:restart"
CB_MOTION = "action:motion"
CB_MOTION_MODE = "motion:mode:"
CB_MOTION_RESTART = "motion:restart"
CB_HUB_TALKING = "hub:talking"
CB_HUB_PHOTO = "hub:photo"
CB_HUB_VIDEO = "hub:video"
CB_HUB_VOICE = "hub:voice"
CB_HUB_HISTORY = "hub:history"
CB_HUB_HOME = "hub:home"
CB_RESTORE = "action:restore"
CB_SCENE = "action:scene"
CB_I2V = "action:i2v"
CB_VOICE = "action:voice"
CB_SINGING = "action:singing"
CB_STICKERS = "action:stickers"
CB_SUBS = "action:subs"
CB_RESTORE_MODE = "restore:mode:"
CB_SCENE_TYPE = "scene:type:"
CB_SCENE_PRESET = "scene:preset:"
CB_I2V_DUR = "i2v:dur:"
CB_VOICE_LANG = "voice:lang:"
CB_CONFIRM_OK = "confirm:ok:"
CB_CONFIRM_NO = "confirm:no"
CB_PIPE_LIP = "pipe:lip:"
CB_PIPE_MOTION = "pipe:motion:"
CB_PIPE_I2V = "pipe:i2v:"
CB_PIPE_SUBS = "pipe:subs:"
CB_PIPE_VOICE_LIP = "pipe:voicelip:"
CB_HIST_RERUN = "hist:rerun:"
CB_FAV_DANCE = "fav:dance:"


def _chunked(items: list[InlineKeyboardButton], size: int) -> list[list[InlineKeyboardButton]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def hub_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗣 Говорящие аватары", callback_data=CB_HUB_TALKING)],
            [InlineKeyboardButton(text="📸 Фото и сцены", callback_data=CB_HUB_PHOTO)],
            [InlineKeyboardButton(text="🎬 Видео-эффекты", callback_data=CB_HUB_VIDEO)],
            [InlineKeyboardButton(text="🎙 Голос", callback_data=CB_HUB_VOICE)],
            [
                InlineKeyboardButton(text="📚 История", callback_data=CB_HUB_HISTORY),
                InlineKeyboardButton(text="⭐ Избранное", callback_data=CB_FAV_LIST),
            ],
        ]
    )


def hub_talking_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐾 Создать персонажа", callback_data=CB_RESTART)],
            [InlineKeyboardButton(text="📷 Своё лицо", callback_data=CB_PHOTO_MODE)],
            [InlineKeyboardButton(text="🐻 Мой маскот", callback_data=CB_MASCOT_MODE)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)],
        ]
    )


def hub_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Нейрофотосессия", callback_data=CB_PHOTOSHOOT)],
            [InlineKeyboardButton(text="🩹 Реставрация фото", callback_data=CB_RESTORE)],
            [InlineKeyboardButton(text="🌍 Сцена / мем", callback_data=CB_SCENE)],
            [InlineKeyboardButton(text="😀 Стикер-пак", callback_data=CB_STICKERS)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)],
        ]
    )


def hub_video_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💃 Motion / Танец", callback_data=CB_MOTION)],
            [InlineKeyboardButton(text="🎥 Видео по промпту", callback_data=CB_I2V)],
            [InlineKeyboardButton(text="🎤 Поющий аватар", callback_data=CB_SINGING)],
            [InlineKeyboardButton(text="📝 Субтитры", callback_data=CB_SUBS)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)],
        ]
    )


def hub_voice_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎙 Клон голоса + текст", callback_data=CB_VOICE)],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)],
        ]
    )


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return hub_menu_keyboard()


def animals_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{meta.emoji} {meta.label_ru}",
            callback_data=f"{CB_ANIMAL}{key}",
        )
        for key, meta in ANIMALS.items()
    ]
    rows = _chunked(buttons, 2)
    rows.append(
        [InlineKeyboardButton(text="✨ Свой вариант", callback_data=f"{CB_ANIMAL}custom")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def genders_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{meta.emoji} {meta.label_ru}",
                callback_data=f"{CB_GENDER}{key}",
            )
        ]
        for key, meta in GENDERS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def styles_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{meta.emoji} {meta.label_ru}",
                callback_data=f"{CB_STYLE}{key}",
            )
        ]
        for key, meta in STYLES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def emotions_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=f"{meta.emoji} {meta.label_ru}",
            callback_data=f"{CB_EMOTION}{key}",
        )
        for key, meta in EMOTIONS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=_chunked(buttons, 2))


def generate_or_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎨 Нарисовать персонажа", callback_data=CB_GENERATE)],
            [InlineKeyboardButton(text="📷 Использовать своё фото", callback_data=CB_USE_PHOTO)],
        ]
    )


def avatar_actions_keyboard(*, can_save: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text="🔄 Перегенерировать", callback_data=CB_REGENERATE),
            InlineKeyboardButton(text="🐾 Другой персонаж", callback_data=CB_RESTART),
        ],
    ]
    if can_save:
        rows.append(
            [InlineKeyboardButton(text="⭐ Сохранить в избранное", callback_data=CB_FAV_SAVE)]
        )
    rows.append([InlineKeyboardButton(text="📚 Мои избранные", callback_data=CB_FAV_LIST)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorite_name_keyboard(suggested_name: str) -> InlineKeyboardMarkup:
    short = suggested_name[:36] + ("…" if len(suggested_name) > 36 else "")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"✅ {short}", callback_data=CB_FAV_NAME_AUTO)],
        ]
    )


def favorites_list_keyboard(favorites: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for fav in favorites:
        label = fav.name[:30] + ("…" if len(fav.name) > 30 else "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"▶️ {label}",
                    callback_data=f"{CB_FAV_USE}{fav.id}",
                ),
                InlineKeyboardButton(
                    text="💃",
                    callback_data=f"{CB_FAV_DANCE}{fav.id}",
                ),
                InlineKeyboardButton(
                    text="🗑",
                    callback_data=f"{CB_FAV_DEL}{fav.id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_cost_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Запустить",
                    callback_data=f"{CB_CONFIRM_OK}{token}",
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=f"{CB_CONFIRM_NO}{token}",
                ),
            ]
        ]
    )


def image_pipeline_keyboard(history_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗣 Оживить (lip-sync)",
                    callback_data=f"{CB_PIPE_LIP}{history_id}",
                ),
                InlineKeyboardButton(
                    text="💃 Танец",
                    callback_data=f"{CB_PIPE_MOTION}{history_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🎥 Видео по промпту",
                    callback_data=f"{CB_PIPE_I2V}{history_id}",
                ),
                InlineKeyboardButton(
                    text="🎤 Пою",
                    callback_data=f"{CB_PIPE_VOICE_LIP}{history_id}",
                ),
            ],
        ]
    )


def video_pipeline_keyboard(history_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📝 Субтитры",
                    callback_data=f"{CB_PIPE_SUBS}{history_id}",
                ),
                InlineKeyboardButton(
                    text="🔄 Re-run",
                    callback_data=f"{CB_HIST_RERUN}{history_id}",
                ),
            ],
        ]
    )


def audio_pipeline_keyboard(history_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗣 Lip-sync с этим аудио",
                    callback_data=f"{CB_PIPE_VOICE_LIP}{history_id}",
                ),
            ],
        ]
    )


def restore_modes_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_RESTORE_MODE}{key}",
            )
        ]
        for key, (label, _) in RESTORE_MODES.items()
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CB_HUB_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def scene_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗼 Известные места",
                    callback_data=f"{CB_SCENE_TYPE}iconic",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Невозможные мемы",
                    callback_data=f"{CB_SCENE_TYPE}impossible",
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CB_HUB_HOME)],
        ]
    )


def scene_presets_keyboard(scene_type: str) -> InlineKeyboardMarkup:
    presets = ICONIC_LOCATIONS if scene_type == "iconic" else IMPOSSIBLE_SCENES
    rows = [
        [
            InlineKeyboardButton(
                text=preset.label_ru,
                callback_data=f"{CB_SCENE_PRESET}{preset.key}",
            )
        ]
        for preset in presets.values()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def i2v_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="5 сек", callback_data=f"{CB_I2V_DUR}5"),
                InlineKeyboardButton(text="10 сек", callback_data=f"{CB_I2V_DUR}10"),
            ]
        ]
    )


def voice_language_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_VOICE_LANG}{key}",
            )
        ]
        for key, label in VOICE_LANGUAGES.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_list_keyboard(items: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in items:
        label = item.title[:28] + ("…" if len(item.title) > 28 else "")
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"🔄 {label}",
                    callback_data=f"{CB_HIST_RERUN}{item.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_HUB_HOME)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def photoshoot_presets_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{preset.emoji} {preset.label_ru}",
                callback_data=f"{CB_PS_PRESET}{key}",
            )
        ]
        for key, preset in PRESETS.items()
    ]
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data=CB_RESTART)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def headshot_background_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_PS_BG}{key}",
            )
        ]
        for key, label in HEADSHOT_BACKGROUNDS.items()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def headshot_gender_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_PS_GENDER}{key}",
            )
        ]
        for key, label in HEADSHOT_GENDERS.items()
    ]
    rows.append(
        [InlineKeyboardButton(text="⏭ Не указывать", callback_data=f"{CB_PS_GENDER}skip")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ftm_styles_keyboard() -> InlineKeyboardMarkup:
    labels = {
        "3d": "🧊 3D",
        "pixel": "👾 Pixel art",
        "clay": "🎭 Claymation",
        "toy": "🧸 Toy",
        "emoji": "😀 Emoji",
        "game": "🎮 Video game",
    }
    buttons = [
        InlineKeyboardButton(
            text=labels.get(key, key),
            callback_data=f"{CB_PS_FTM}{key}",
        )
        for key in FACE_TO_MANY_STYLES
    ]
    return InlineKeyboardMarkup(inline_keyboard=_chunked(buttons, 2))


def photomaker_styles_keyboard() -> InlineKeyboardMarkup:
    labels = {
        "photo": "📷 Фото",
        "cinematic": "🎬 Кино",
        "digital": "🖥 Digital Art",
        "fantasy": "🧙 Fantasy",
        "neon": "🌃 Neonpunk",
        "comic": "💥 Comic",
        "line": "✏️ Line art",
        "disney": "🏰 Disney",
    }
    rows = [
        [
            InlineKeyboardButton(
                text=labels.get(key, key),
                callback_data=f"{CB_PS_PM}{key}",
            )
        ]
        for key in PHOTOMAKER_STYLES
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def photoshoot_photos_done_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ Готово ({count} фото)",
                    callback_data=CB_PS_PHOTOS_DONE,
                )
            ],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=CB_PS_RESTART)],
        ]
    )


def motion_modes_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{mode.emoji} {mode.label_ru}",
                callback_data=f"{CB_MOTION_MODE}{key}",
            )
        ]
        for key, mode in MODES.items()
    ]
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data=CB_MOTION_RESTART)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
