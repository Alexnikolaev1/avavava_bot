from __future__ import annotations

import asyncio
import json

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.common import check_cooldown
from bot.keyboards import confirm_cost_keyboard
from bot.services.history import HistoryItem, HistoryStore
from bot.services.pending import PendingJob, PendingStore
from bot.services.pricing import CostEstimate
from bot.states import I2VFlow, MotionFlow, PhotoFlow, SingingFlow, SubtitlesFlow
from bot.texts import MOTION_SEND_VIDEO, PHOTO_MODE_START


async def offer_confirm(
    message: Message,
    pending: PendingStore,
    user_id: int,
    action: str,
    payload: dict,
    cost: CostEstimate,
) -> None:
    token = pending.put(
        PendingJob(
            user_id=user_id,
            action=action,
            payload=payload,
            cost_text=cost.format_message(),
        )
    )
    await message.answer(
        f"💰 <b>Оценка стоимости</b>\n{cost.format_message()}\n\nЗапустить генерацию?",
        reply_markup=confirm_cost_keyboard(token),
    )


async def execute_pending(
    job: PendingJob,
    *,
    message: Message,
    state: FSMContext,
    settings: Settings,
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
    action = job.action
    payload = job.payload
    user_id = job.user_id

    wait = check_cooldown(user_id, settings)
    if wait is not None:
        await message.answer(f"Слишком часто. Подожди ещё {wait} сек.")
        return

    if action == "motion":
        from bot.services.motion import MotionJob

        status = await message.answer("Принял в обработку. Это может занять 5–15 минут...")
        motion_job = MotionJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            mode=payload["mode"],
            video_file_id=payload["video_file_id"],
            photo_file_id=payload["photo_file_id"],
        )
        asyncio.create_task(motion.run(motion_job))
        return

    if action == "photoshoot":
        from bot.services.photoshoot import PhotoshootJob

        status = await message.answer("Принял в обработку. Генерирую фото...")
        ps_job = PhotoshootJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            preset=payload["preset"],
            photo_file_ids=payload["photo_file_ids"],
            gender=payload.get("gender"),
            background=payload.get("background", "neutral"),
            ftm_style_key=payload.get("ftm_style_key", "3d"),
            pm_style_key=payload.get("pm_style_key", "photo"),
            custom_prompt=payload.get("custom_prompt"),
        )
        asyncio.create_task(photoshoot.run(ps_job))
        return

    if action == "i2v":
        from bot.services.i2v import I2VJob

        status = await message.answer("Генерирую видео по промпту...")
        i2v_job = I2VJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            photo_file_id=payload["photo_file_id"],
            prompt=payload["prompt"],
            duration=int(payload.get("duration", 5)),
        )
        asyncio.create_task(i2v.run(i2v_job))
        return

    if action == "voice":
        from bot.services.voice import VoiceJob

        status = await message.answer("Озвучиваю текст клонированным голосом...")
        voice_job = VoiceJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            sample_file_id=payload["sample_file_id"],
            text=payload["text"],
            language=payload.get("language", "ru"),
        )
        asyncio.create_task(voice.run(voice_job))
        return

    if action == "singing":
        from bot.services.singing import SingingJob

        status = await message.answer("Создаю поющий аватар...")
        sing_job = SingingJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            photo_file_id=payload["photo_file_id"],
            audio_file_id=payload["audio_file_id"],
        )
        asyncio.create_task(singing.run(sing_job))
        return

    if action == "restore":
        from bot.services.creative import CreativeJob

        status = await message.answer("Обрабатываю фото...")
        cr_job = CreativeJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            kind="restore",
            photo_file_id=payload["photo_file_id"],
            mode=payload.get("mode", "restore"),
        )
        asyncio.create_task(creative.run(cr_job))
        return

    if action == "scene":
        from bot.services.creative import CreativeJob

        status = await message.answer("Создаю сцену...")
        cr_job = CreativeJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            kind="scene",
            photo_file_id=payload["photo_file_id"],
            scene_type=payload.get("scene_type", "iconic"),
            scene_key=payload.get("scene_key", "eiffel"),
        )
        asyncio.create_task(creative.run(cr_job))
        return

    if action == "stickers":
        from bot.services.stickers import StickerJob

        status = await message.answer("Создаю стикер-пак...")
        st_job = StickerJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            photo_file_id=payload["photo_file_id"],
        )
        asyncio.create_task(stickers.run(st_job))
        return

    if action == "subtitles":
        from bot.services.subtitles import SubtitlesJob

        status = await message.answer("Добавляю субтитры...")
        sub_job = SubtitlesJob(
            chat_id=message.chat.id,
            user_id=user_id,
            status_message_id=status.message_id,
            video_file_id=payload["video_file_id"],
        )
        asyncio.create_task(subtitles.run(sub_job))
        return

    await message.answer(f"Неизвестное действие: {action}")


async def rerun_history_item(
    callback: CallbackQuery,
    history: HistoryStore,
    item_id: int,
) -> None:
    item = await history.get(callback.from_user.id, item_id)
    if not item:
        await callback.answer("Запись не найдена", show_alert=True)
        return

    from bot.handlers.pipeline import start_pipeline_from_history

    await start_pipeline_from_history(callback.message, callback.bot, item, rerun=True)


async def start_lip_sync_with_image(
    message: Message,
    state: FSMContext,
    image_file_id: str,
    *,
    engine: str = "auto",
) -> None:
    await state.clear()
    await state.update_data(avatar_file_id=image_file_id, pipeline_engine=engine)
    await state.set_state(PhotoFlow.waiting_for_audio)
    await message.answer(
        "Фото готово. Пришли аудио (voice или файл) — сделаю говорящее видео."
    )


async def start_motion_with_photo(
    message: Message,
    state: FSMContext,
    settings: Settings,
    photo_file_id: str,
    mode: str = "kling",
) -> None:
    await state.update_data(mode=mode, photo_file_id=photo_file_id, pipeline_photo=True)
    await state.set_state(MotionFlow.waiting_for_video)
    await message.answer(
        MOTION_SEND_VIDEO.format(max_seconds=settings.motion_max_video_seconds)
    )


async def start_i2v_with_photo(
    message: Message,
    state: FSMContext,
    photo_file_id: str,
) -> None:
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(I2VFlow.waiting_for_prompt)
    await message.answer(
        "Опиши, что должно происходить на видео.\n"
        "Например: <i>человек идёт по дождливому городу, кинематографично</i>"
    )


async def start_singing_with_photo(
    message: Message,
    state: FSMContext,
    photo_file_id: str,
) -> None:
    await state.update_data(photo_file_id=photo_file_id)
    await state.set_state(SingingFlow.waiting_for_audio)
    await message.answer(
        "Пришли песню или voice — сделаю поющий аватар (Kling)."
    )


async def start_singing_with_audio(
    message: Message,
    state: FSMContext,
    audio_file_id: str,
    *,
    duration: int = 10,
) -> None:
    await state.clear()
    await state.update_data(audio_file_id=audio_file_id, audio_duration=duration)
    await state.set_state(SingingFlow.waiting_for_photo)
    await message.answer("Пришли фото персонажа для поющего аватара.")
