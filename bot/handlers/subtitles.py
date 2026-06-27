from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.jobs import offer_confirm
from bot.keyboards import CB_SUBS, hub_video_keyboard
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_subtitles
from bot.states import SubtitlesFlow
from bot.texts import SUBS_SEND_VIDEO

router = Router()


@router.callback_query(F.data == CB_SUBS)
async def cb_subs(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SubtitlesFlow.waiting_for_video)
    await callback.message.answer(SUBS_SEND_VIDEO)
    await callback.answer()


@router.message(Command("subtitles"))
async def cmd_subs(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SubtitlesFlow.waiting_for_video)
    await message.answer(SUBS_SEND_VIDEO)


@router.message(StateFilter(SubtitlesFlow.waiting_for_video), F.video)
async def subs_video(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    await state.clear()
    cost = estimate_subtitles()
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "subtitles",
        {"video_file_id": message.video.file_id},
        cost,
    )


@router.message(StateFilter(SubtitlesFlow.waiting_for_video), F.document)
async def subs_video_doc(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        await message.answer("Жду видеофайл mp4/mov.")
        return
    await state.clear()
    cost = estimate_subtitles()
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "subtitles",
        {"video_file_id": doc.file_id},
        cost,
    )
