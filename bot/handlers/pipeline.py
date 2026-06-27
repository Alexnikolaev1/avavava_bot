from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.jobs import (
    execute_pending,
    start_i2v_with_photo,
    start_lip_sync_with_image,
    start_motion_with_photo,
    start_singing_with_audio,
    start_singing_with_photo,
)
from bot.keyboards import (
    CB_CONFIRM_NO,
    CB_CONFIRM_OK,
    CB_PIPE_I2V,
    CB_PIPE_LIP,
    CB_PIPE_MOTION,
    CB_PIPE_SUBS,
    CB_PIPE_VOICE_LIP,
)
from bot.services.history import HistoryItem, HistoryStore
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_subtitles
from bot.handlers.jobs import offer_confirm

router = Router()


@router.callback_query(F.data.startswith(CB_CONFIRM_OK))
async def cb_confirm_ok(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
    motion,
    photoshoot,
    i2v,
    voice,
    singing,
    creative,
    stickers,
    subtitles,
    pipeline,
) -> None:
    token = callback.data.removeprefix(CB_CONFIRM_OK)
    job = pending.pop(token, callback.from_user.id)
    if not job:
        await callback.answer("Задача устарела", show_alert=True)
        return
    await callback.answer("Запускаю...")
    await execute_pending(
        job,
        message=callback.message,
        state=state,
        settings=settings,
        motion=motion,
        photoshoot=photoshoot,
        i2v=i2v,
        voice=voice,
        singing=singing,
        creative=creative,
        stickers=stickers,
        subtitles=subtitles,
        pipeline=pipeline,
    )


@router.callback_query(F.data.startswith(CB_CONFIRM_NO))
async def cb_confirm_no(callback: CallbackQuery, pending: PendingStore) -> None:
    token = callback.data.removeprefix(CB_CONFIRM_NO)
    pending.pop(token, callback.from_user.id)
    await callback.message.edit_text("Отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PIPE_LIP))
async def cb_pipe_lip(
    callback: CallbackQuery,
    state: FSMContext,
    history: HistoryStore,
) -> None:
    item_id = int(callback.data.removeprefix(CB_PIPE_LIP))
    item = await history.get(callback.from_user.id, item_id)
    if not item or not item.image_file_id:
        await callback.answer("Нет фото в записи", show_alert=True)
        return
    await start_lip_sync_with_image(callback.message, state, item.image_file_id)
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PIPE_MOTION))
async def cb_pipe_motion(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    history: HistoryStore,
) -> None:
    item_id = int(callback.data.removeprefix(CB_PIPE_MOTION))
    item = await history.get(callback.from_user.id, item_id)
    if not item or not item.image_file_id:
        await callback.answer("Нет фото", show_alert=True)
        return
    await start_motion_with_photo(
        callback.message, state, settings, item.image_file_id, mode="kling"
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PIPE_I2V))
async def cb_pipe_i2v(
    callback: CallbackQuery,
    state: FSMContext,
    history: HistoryStore,
) -> None:
    item_id = int(callback.data.removeprefix(CB_PIPE_I2V))
    item = await history.get(callback.from_user.id, item_id)
    if not item or not item.image_file_id:
        await callback.answer("Нет фото", show_alert=True)
        return
    await start_i2v_with_photo(callback.message, state, item.image_file_id)
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PIPE_VOICE_LIP))
async def cb_pipe_voice_lip(
    callback: CallbackQuery,
    state: FSMContext,
    history: HistoryStore,
) -> None:
    item_id = int(callback.data.removeprefix(CB_PIPE_VOICE_LIP))
    item = await history.get(callback.from_user.id, item_id)
    if not item:
        await callback.answer("Запись не найдена", show_alert=True)
        return
    if item.kind == "voice" and item.audio_file_id:
        await start_singing_with_audio(
            callback.message,
            state,
            item.audio_file_id,
            duration=int(item.meta.get("duration", 10)),
        )
    elif item.image_file_id:
        await start_singing_with_photo(callback.message, state, item.image_file_id)
    else:
        await callback.answer("Нет подходящих данных", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith(CB_PIPE_SUBS))
async def cb_pipe_subs(
    callback: CallbackQuery,
    pending: PendingStore,
    history: HistoryStore,
) -> None:
    item_id = int(callback.data.removeprefix(CB_PIPE_SUBS))
    item = await history.get(callback.from_user.id, item_id)
    if not item or not item.video_file_id:
        await callback.answer("Нет видео", show_alert=True)
        return
    cost = estimate_subtitles()
    await offer_confirm(
        callback.message,
        pending,
        callback.from_user.id,
        "subtitles",
        {"video_file_id": item.video_file_id},
        cost,
    )
    await callback.answer()


async def start_pipeline_from_history(
    message: Message,
    bot,
    item: HistoryItem,
    *,
    rerun: bool = False,
) -> None:
    if item.video_file_id and rerun:
        await message.answer(
            f"Re-run: «{item.title}»\nИспользуй кнопки под результатом или /history."
        )
        return
    if item.image_file_id:
        from bot.keyboards import image_pipeline_keyboard

        await message.answer(
            f"«{item.title}» — что сделать дальше?",
            reply_markup=image_pipeline_keyboard(item.id),
        )
        return
    await message.answer("Для этой записи нет быстрых действий.")
