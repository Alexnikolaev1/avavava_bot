from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import (
    CB_HUB_HISTORY,
    CB_HUB_HOME,
    CB_HUB_PHOTO,
    CB_HUB_TALKING,
    CB_HUB_VIDEO,
    CB_HUB_VOICE,
    hub_menu_keyboard,
    hub_photo_keyboard,
    hub_talking_keyboard,
    hub_video_keyboard,
    hub_voice_keyboard,
)
from bot.states import AvatarFlow
from bot.texts import HUB_PHOTO, HUB_TALKING, HUB_VIDEO, HUB_VOICE

router = Router()


@router.callback_query(F.data == CB_HUB_HOME)
async def cb_hub_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Главное меню 👇", reply_markup=hub_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_HUB_TALKING)
async def cb_hub_talking(callback: CallbackQuery) -> None:
    await callback.message.answer(HUB_TALKING, reply_markup=hub_talking_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_HUB_PHOTO)
async def cb_hub_photo(callback: CallbackQuery) -> None:
    await callback.message.answer(HUB_PHOTO, reply_markup=hub_photo_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_HUB_VIDEO)
async def cb_hub_video(callback: CallbackQuery) -> None:
    await callback.message.answer(HUB_VIDEO, reply_markup=hub_video_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_HUB_VOICE)
async def cb_hub_voice(callback: CallbackQuery) -> None:
    await callback.message.answer(HUB_VOICE, reply_markup=hub_voice_keyboard())
    await callback.answer()


@router.callback_query(F.data == CB_HUB_HISTORY)
async def cb_hub_history(callback: CallbackQuery, history: HistoryStore) -> None:
    from bot.handlers.history import show_history_list

    await show_history_list(
        callback.message, callback.from_user.id, history, edit=False,
    )
    await callback.answer()
