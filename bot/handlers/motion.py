from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.jobs import offer_confirm
from bot.keyboards import (
    CB_MOTION,
    CB_MOTION_MODE,
    CB_MOTION_RESTART,
    main_menu_keyboard,
    motion_modes_keyboard,
)
from bot.motion_catalog import MODES
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_motion
from bot.states import MotionFlow
from bot.texts import MOTION_SEND_PHOTO, MOTION_SEND_VIDEO, MOTION_START

router = Router()


async def _start_motion(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(MotionFlow.choosing_mode)
    await message.answer(MOTION_START, reply_markup=motion_modes_keyboard())


@router.callback_query(F.data == CB_MOTION)
async def cb_motion(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_motion(callback.message, state)
    await callback.answer()


@router.message(Command("motion"))
async def cmd_motion(message: Message, state: FSMContext) -> None:
    await _start_motion(message, state)


@router.message(Command("dance"))
async def cmd_dance(message: Message, state: FSMContext) -> None:
    await _start_motion(message, state)


@router.callback_query(
    StateFilter(MotionFlow.choosing_mode),
    F.data.startswith(CB_MOTION_MODE),
)
async def cb_choose_mode(callback: CallbackQuery, state: FSMContext, settings: Settings) -> None:
    mode_key = callback.data.removeprefix(CB_MOTION_MODE)
    if mode_key not in MODES:
        await callback.answer("Неизвестный режим", show_alert=True)
        return

    await state.update_data(mode=mode_key)
    await state.set_state(MotionFlow.waiting_for_video)
    await callback.message.answer(
        MOTION_SEND_VIDEO.format(max_seconds=settings.motion_max_video_seconds),
    )
    await callback.answer()


@router.callback_query(F.data == CB_MOTION_RESTART)
async def cb_motion_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "Motion control отменён. Главное меню 👇",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(MotionFlow.waiting_for_video), F.video)
async def receive_video(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    video = message.video
    if video.duration and video.duration > settings.motion_max_video_seconds:
        await message.answer(
            f"Видео {video.duration} сек. — лимит {settings.motion_max_video_seconds} сек. "
            "Пришли покороче или обрежь клип."
        )
        return
    await _after_video_received(message, state, settings, pending, video.file_id, video.duration)


@router.message(StateFilter(MotionFlow.waiting_for_video), F.document)
async def receive_video_document(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    doc = message.document
    if not doc.mime_type or not doc.mime_type.startswith("video/"):
        await message.answer("Жду видеофайл (mp4/mov) или отправь как видео, не документ.")
        return
    await _after_video_received(message, state, settings, pending, doc.file_id, None)


@router.message(StateFilter(MotionFlow.waiting_for_video))
async def wrong_video(message: Message) -> None:
    await message.answer("Жду видео с танцем/движением (как видео или mp4-файл).")


@router.message(StateFilter(MotionFlow.waiting_for_photo), F.photo)
async def receive_photo(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    mode = data.get("mode")
    if not video_file_id or not mode:
        await message.answer("Начни заново: /motion")
        await state.clear()
        return
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await _offer_motion_confirm(message, state, settings, pending, message.from_user.id)


async def _after_video_received(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
    video_file_id: str,
    duration: int | None,
) -> None:
    await state.update_data(video_file_id=video_file_id, video_duration=duration)
    data = await state.get_data()
    if data.get("pipeline_photo") and data.get("photo_file_id"):
        await _offer_motion_confirm(message, state, settings, pending, message.from_user.id)
        return
    await state.set_state(MotionFlow.waiting_for_photo)
    await message.answer(MOTION_SEND_PHOTO)


async def _offer_motion_confirm(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
    user_id: int,
) -> None:
    data = await state.get_data()
    mode = data.get("mode", "kling")
    seconds = data.get("video_duration") or settings.motion_max_video_seconds
    seconds = min(int(seconds), settings.motion_max_video_seconds)
    cost = estimate_motion(mode, seconds, kling_mode=settings.motion_kling_mode)
    payload = {
        "mode": mode,
        "video_file_id": data["video_file_id"],
        "photo_file_id": data["photo_file_id"],
    }
    await state.clear()
    await offer_confirm(message, pending, user_id, "motion", payload, cost)


@router.message(StateFilter(MotionFlow.waiting_for_photo))
async def wrong_photo(message: Message) -> None:
    await message.answer("Жду фото лица или персонажа (как изображение).")
