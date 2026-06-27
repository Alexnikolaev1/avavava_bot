from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.jobs import offer_confirm
from bot.keyboards import CB_SINGING, CB_STICKERS, hub_photo_keyboard, hub_video_keyboard
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_singing, estimate_stickers
from bot.states import SingingFlow, StickerFlow
from bot.texts import SINGING_PHOTO, SINGING_AUDIO, STICKERS_PHOTO

router = Router()


@router.callback_query(F.data == CB_SINGING)
async def cb_singing(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SingingFlow.waiting_for_photo)
    await callback.message.answer(SINGING_PHOTO)
    await callback.answer()


@router.message(Command("singing"))
async def cmd_singing(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SingingFlow.waiting_for_photo)
    await message.answer(SINGING_PHOTO)


@router.message(StateFilter(SingingFlow.waiting_for_photo), F.photo)
async def singing_photo(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    data = await state.get_data()
    audio_file_id = data.get("audio_file_id")
    if audio_file_id:
        duration = int(data.get("audio_duration", 10))
        await state.clear()
        cost = estimate_singing(duration)
        await offer_confirm(
            message,
            pending,
            message.from_user.id,
            "singing",
            {
                "photo_file_id": message.photo[-1].file_id,
                "audio_file_id": audio_file_id,
            },
            cost,
        )
        return
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(SingingFlow.waiting_for_audio)
    await message.answer(SINGING_AUDIO)


@router.message(StateFilter(SingingFlow.waiting_for_audio), F.audio | F.voice)
async def singing_audio(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    audio = message.audio or message.voice
    duration = getattr(audio, "duration", 10) or 10
    if duration > settings.max_audio_seconds:
        await message.answer(f"Аудио до {settings.max_audio_seconds} сек.")
        return
    data = await state.get_data()
    await state.clear()
    cost = estimate_singing(duration)
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "singing",
        {
            "photo_file_id": data["photo_file_id"],
            "audio_file_id": audio.file_id,
        },
        cost,
    )


@router.callback_query(F.data == CB_STICKERS)
async def cb_stickers(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StickerFlow.waiting_for_photo)
    await callback.message.answer(STICKERS_PHOTO)
    await callback.answer()


@router.message(Command("stickers"))
async def cmd_stickers(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(StickerFlow.waiting_for_photo)
    await message.answer(STICKERS_PHOTO)


@router.message(StateFilter(StickerFlow.waiting_for_photo), F.photo)
async def stickers_photo(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    await state.clear()
    cost = estimate_stickers()
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "stickers",
        {"photo_file_id": message.photo[-1].file_id},
        cost,
    )
