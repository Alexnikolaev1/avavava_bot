from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.keyboards import CB_HIST_RERUN, history_list_keyboard, hub_menu_keyboard
from bot.services.history import HistoryStore
from bot.texts import HISTORY_EMPTY, HISTORY_HEADER

router = Router()


async def show_history_list(
    message: Message,
    user_id: int,
    history: HistoryStore,
    *,
    edit: bool = False,
) -> None:
    from aiogram.exceptions import TelegramBadRequest

    items = await history.list_for_user(user_id)
    if not items:
        text = HISTORY_EMPTY
        markup = hub_menu_keyboard()
    else:
        text = HISTORY_HEADER
        markup = history_list_keyboard(items)

    if edit:
        try:
            await message.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            await message.answer(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


@router.message(Command("history"))
async def cmd_history(message: Message, history: HistoryStore) -> None:
    await show_history_list(message, message.from_user.id, history)


@router.callback_query(F.data.startswith(CB_HIST_RERUN))
async def cb_history_rerun(callback: CallbackQuery, history: HistoryStore) -> None:
    from bot.handlers.jobs import rerun_history_item

    item_id = int(callback.data.removeprefix(CB_HIST_RERUN))
    await rerun_history_item(callback, history, item_id)
    await callback.answer()
