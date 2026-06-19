from __future__ import annotations

import time
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.keyboards import animals_keyboard, main_menu_keyboard
from bot.services.favorites import FavoritesStore
from bot.states import AvatarFlow
from bot.texts import FAV_EMPTY, FAV_LIST_HEADER, HELP_TEXT, WELCOME

if TYPE_CHECKING:
    from bot.config import Settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AvatarFlow.choosing_animal)
    await message.answer(WELCOME, reply_markup=main_menu_keyboard())
    await message.answer("Кого нарисуем? Выбери животное 👇", reply_markup=animals_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Отменено. Нажми /start для нового персонажа.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(StateFilter(None))
async def fallback(message: Message) -> None:
    await message.answer(
        "Напиши /start, чтобы создать говорящего персонажа.",
        reply_markup=main_menu_keyboard(),
    )


async def show_favorites_list(
    message: Message,
    favorites: FavoritesStore,
    user_id: int,
    *,
    edit: bool = False,
) -> None:
    from aiogram.exceptions import TelegramBadRequest
    from bot.keyboards import favorites_list_keyboard

    items = await favorites.list_for_user(user_id)
    if not items:
        text = FAV_EMPTY
        markup = main_menu_keyboard()
    else:
        text = FAV_LIST_HEADER
        markup = favorites_list_keyboard(items)

    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


def check_cooldown(user_id: int, settings: Settings) -> int | None:
    """Возвращает секунд ожидания или None, если можно продолжать."""
    storage = check_cooldown.__dict__
    last_map: dict[int, float] = storage.setdefault("_last", {})
    now = time.monotonic()
    last = last_map.get(user_id, 0.0)
    delta = now - last
    if delta < settings.user_cooldown_seconds:
        return int(settings.user_cooldown_seconds - delta)
    last_map[user_id] = now
    return None
