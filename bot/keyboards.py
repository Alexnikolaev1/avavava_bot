from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.catalog import ANIMALS, EMOTIONS, GENDERS, STYLES

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


def _chunked(items: list[InlineKeyboardButton], size: int) -> list[list[InlineKeyboardButton]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🐾 Создать персонажа", callback_data=CB_RESTART)],
            [
                InlineKeyboardButton(text="🐻 Мой маскот", callback_data=CB_MASCOT_MODE),
                InlineKeyboardButton(text="⭐ Избранное", callback_data=CB_FAV_LIST),
            ],
            [InlineKeyboardButton(text="📷 Своё лицо", callback_data=CB_PHOTO_MODE)],
        ]
    )


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
                    text="🗑",
                    callback_data=f"{CB_FAV_DEL}{fav.id}",
                ),
            ]
        )
    rows.append([InlineKeyboardButton(text="🐾 Новый персонаж", callback_data=CB_RESTART)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
