from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.common import check_cooldown
from bot.keyboards import CB_MASCOT_MODE
from bot.services.pipeline import GenerationPipeline, VideoJob
from bot.states import MascotFlow
from bot.texts import MASCOT_MODE_START, STATUS

router = Router()


@router.callback_query(F.data == CB_MASCOT_MODE)
async def cb_mascot_mode(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(MascotFlow.waiting_for_photo)
    await callback.message.answer(MASCOT_MODE_START)
    await callback.answer()


@router.message(Command("mascot"))
async def cmd_mascot_mode(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(MascotFlow.waiting_for_photo)
    await message.answer(MASCOT_MODE_START)


@router.message(StateFilter(MascotFlow.waiting_for_photo), F.photo)
async def mascot_receive_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(avatar_file_id=message.photo[-1].file_id)
    await state.set_state(MascotFlow.waiting_for_audio)
    await message.answer(
        "Маскот получил! 🐻\n"
        "Теперь пришли аудио (voice или файл) — оживлю его."
    )


@router.message(StateFilter(MascotFlow.waiting_for_photo))
async def mascot_wrong_input(message: Message) -> None:
    await message.answer("Жду фото маскота или персонажа (как изображение).")


@router.message(StateFilter(MascotFlow.waiting_for_audio), F.audio | F.voice)
async def mascot_receive_audio(
    message: Message,
    state: FSMContext,
    pipeline: GenerationPipeline,
    settings: Settings,
) -> None:
    data = await state.get_data()
    avatar_file_id = data.get("avatar_file_id")
    if not avatar_file_id:
        await message.answer("Начни заново: /mascot")
        await state.clear()
        return

    audio = message.audio or message.voice
    duration = getattr(audio, "duration", None)
    if duration and duration > settings.max_audio_seconds:
        await message.answer(
            f"Аудио {duration} сек. — лимит {settings.max_audio_seconds} сек."
        )
        return

    wait = check_cooldown(message.from_user.id, settings)
    if wait is not None:
        await message.answer(f"Слишком часто. Подожди ещё {wait} сек.")
        return

    await state.clear()
    status = await message.answer(STATUS["queued"])
    asyncio.create_task(
        pipeline.generate_video(
            VideoJob(
                chat_id=message.chat.id,
                status_message_id=status.message_id,
                image_file_id=avatar_file_id,
                audio_file_id=audio.file_id,
                audio_duration=duration,
                cartoon=True,
                engine="kling",
            )
        )
    )


@router.message(StateFilter(MascotFlow.waiting_for_audio))
async def mascot_wrong_audio(message: Message) -> None:
    await message.answer("Жду аудиофайл или voice-сообщение.")
