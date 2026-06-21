from __future__ import annotations

import asyncio

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.catalog import ANIMALS, EMOTIONS, GENDERS, STYLES
from bot.config import Settings
from bot.handlers.common import check_cooldown
from bot.keyboards import (
    CB_ANIMAL,
    CB_EMOTION,
    CB_GENERATE,
    CB_GENDER,
    CB_REGENERATE,
    CB_RESTART,
    CB_STYLE,
    CB_USE_PHOTO,
    animals_keyboard,
    avatar_actions_keyboard,
    emotions_keyboard,
    genders_keyboard,
    generate_or_photo_keyboard,
    styles_keyboard,
)
from bot.models.avatar_config import AvatarConfig
from bot.services.pipeline import AvatarJob, GenerationPipeline, VideoJob
from bot.states import AvatarFlow
from bot.texts import (
    CHOOSE_ANIMAL,
    CHOOSE_EMOTION,
    CHOOSE_GENDER,
    CHOOSE_STYLE,
    CUSTOM_ANIMAL_PROMPT,
    PHOTO_OR_GENERATE,
    STATUS,
    avatar_ready_text,
)

router = Router()


@router.callback_query(F.data == CB_RESTART)
async def restart_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AvatarFlow.choosing_animal)
    await callback.message.edit_text(CHOOSE_ANIMAL, reply_markup=animals_keyboard())
    await callback.answer()


@router.callback_query(StateFilter(AvatarFlow.choosing_animal), F.data.startswith(CB_ANIMAL))
async def pick_animal(callback: CallbackQuery, state: FSMContext) -> None:
    key = callback.data.removeprefix(CB_ANIMAL)
    if key == "custom":
        await state.set_state(AvatarFlow.waiting_custom_animal)
        await callback.message.edit_text(CUSTOM_ANIMAL_PROMPT)
        await callback.answer()
        return

    if key not in ANIMALS:
        await callback.answer("Неизвестное животное", show_alert=True)
        return

    await state.update_data(animal_key=key, custom_animal=None)
    await state.set_state(AvatarFlow.choosing_gender)
    meta = ANIMALS[key]
    await callback.message.edit_text(
        f"{meta.emoji} {meta.label_ru}\n\n{CHOOSE_GENDER}",
        reply_markup=genders_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(AvatarFlow.waiting_custom_animal), F.text)
async def custom_animal_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Опиши персонажа чуть подробнее (минимум 2 символа).")
        return
    if len(text) > 120:
        await message.answer("Слишком длинное описание — уложись в 120 символов.")
        return

    await state.update_data(custom_animal=text, animal_key=None)
    await state.set_state(AvatarFlow.choosing_gender)
    await message.answer(CHOOSE_GENDER, reply_markup=genders_keyboard())


@router.message(StateFilter(AvatarFlow.waiting_custom_animal))
async def custom_animal_invalid(message: Message) -> None:
    await message.answer("Пришли текстовое описание персонажа.")


@router.callback_query(StateFilter(AvatarFlow.choosing_gender), F.data.startswith(CB_GENDER))
async def pick_gender(callback: CallbackQuery, state: FSMContext) -> None:
    gender_key = callback.data.removeprefix(CB_GENDER)
    if gender_key not in GENDERS:
        await callback.answer("Неизвестный вариант", show_alert=True)
        return

    await state.update_data(gender_key=gender_key)
    await state.set_state(AvatarFlow.choosing_style)
    gender = GENDERS[gender_key]
    await callback.message.edit_text(
        f"{gender.emoji} {gender.label_ru}\n\n{CHOOSE_STYLE}",
        reply_markup=styles_keyboard(),
    )
    await callback.answer()


@router.callback_query(StateFilter(AvatarFlow.choosing_style), F.data.startswith(CB_STYLE))
async def pick_style(callback: CallbackQuery, state: FSMContext) -> None:
    style_key = callback.data.removeprefix(CB_STYLE)
    if style_key not in STYLES:
        await callback.answer("Неизвестный стиль", show_alert=True)
        return

    await state.update_data(style_key=style_key)
    await state.set_state(AvatarFlow.choosing_emotion)
    style = STYLES[style_key]
    await callback.message.edit_text(
        f"{style.emoji} {style.label_ru}\n\n{CHOOSE_EMOTION}",
        reply_markup=emotions_keyboard(),
    )
    await callback.answer()


@router.callback_query(StateFilter(AvatarFlow.choosing_emotion), F.data.startswith(CB_EMOTION))
async def pick_emotion(callback: CallbackQuery, state: FSMContext) -> None:
    emotion_key = callback.data.removeprefix(CB_EMOTION)
    if emotion_key not in EMOTIONS:
        await callback.answer("Неизвестная эмоция", show_alert=True)
        return

    await state.update_data(emotion_key=emotion_key)
    await state.set_state(AvatarFlow.waiting_photo_or_generate)
    config = AvatarConfig.from_fsm(await state.get_data())
    await callback.message.edit_text(
        f"{config.summary()}\n\n{PHOTO_OR_GENERATE}",
        reply_markup=generate_or_photo_keyboard(),
    )
    await callback.answer()


@router.callback_query(StateFilter(AvatarFlow.waiting_photo_or_generate), F.data == CB_USE_PHOTO)
async def choose_user_photo(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Пришли фото лица — анфас, хорошее освещение, без солнцезащитных очков."
    )
    await callback.answer()


@router.message(StateFilter(AvatarFlow.waiting_photo_or_generate), F.photo)
async def receive_user_photo(message: Message, state: FSMContext) -> None:
    photo_id = message.photo[-1].file_id
    await state.update_data(avatar_file_id=photo_id, source="photo")
    await state.set_state(AvatarFlow.waiting_for_audio)
    await message.answer(
        "Фото получил! Пришли аудио — сделаю говорящее видео.",
        reply_markup=avatar_actions_keyboard(can_save=False),
    )


@router.callback_query(F.data.in_({CB_GENERATE, CB_REGENERATE}))
async def generate_avatar(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    pipeline: GenerationPipeline,
) -> None:
    data = await state.get_data()
    config = AvatarConfig.from_fsm(data)
    if not config.animal_key and not config.custom_animal:
        await callback.answer("Сначала выбери персонажа: /start", show_alert=True)
        return

    if pipeline.active_jobs >= pipeline.max_concurrent_jobs:
        await callback.answer(
            "Сейчас все слоты заняты — запрос встанет в очередь.",
            show_alert=False,
        )

    status = await callback.message.answer(STATUS["drawing"])
    job = AvatarJob(
        chat_id=callback.message.chat.id,
        status_message_id=status.message_id,
        config=config,
    )

    await callback.answer("Рисую персонажа...")
    file_id = await pipeline.generate_avatar(job)
    if file_id:
        await state.update_data(avatar_file_id=file_id, source="generated")
        await state.set_state(AvatarFlow.waiting_for_audio)
        await bot.send_message(
            callback.message.chat.id,
            avatar_ready_text(config.summary()),
            reply_markup=avatar_actions_keyboard(),
        )


@router.message(StateFilter(AvatarFlow.waiting_for_audio), F.audio | F.voice)
async def receive_audio(
    message: Message,
    state: FSMContext,
    pipeline: GenerationPipeline,
    settings: Settings,
) -> None:
    data = await state.get_data()
    avatar_file_id = data.get("avatar_file_id")
    if not avatar_file_id:
        await message.answer("Персонаж не найден. Начни заново: /start")
        await state.clear()
        return

    audio = message.audio or message.voice
    duration = getattr(audio, "duration", None)
    if duration and duration > settings.max_audio_seconds:
        await message.answer(
            f"Аудио {duration} сек. — лимит {settings.max_audio_seconds} сек. "
            "Пришли запись покороче."
        )
        return

    wait = check_cooldown(message.from_user.id, settings)
    if wait is not None:
        await message.answer(f"Слишком часто. Подожди ещё {wait} сек.")
        return

    if pipeline.active_jobs >= pipeline.max_concurrent_jobs:
        await message.answer(
            "Сейчас обрабатываются другие запросы — твой встанет в очередь."
        )

    status = await message.answer(STATUS["queued"])
    source = data.get("source", "generated")
    asyncio.create_task(
        pipeline.generate_video(
            VideoJob(
                chat_id=message.chat.id,
                status_message_id=status.message_id,
                image_file_id=avatar_file_id,
                audio_file_id=audio.file_id,
                audio_duration=duration,
                cartoon=source != "photo",
                kling_fallback=True,
            )
        )
    )


@router.message(StateFilter(AvatarFlow.waiting_for_audio))
async def waiting_audio_invalid(message: Message) -> None:
    await message.answer("Жду аудиофайл или voice-сообщение.")


@router.message(StateFilter(AvatarFlow.waiting_photo_or_generate))
async def waiting_photo_invalid(message: Message) -> None:
    await message.answer(
        "Выбери кнопку «Нарисовать» или пришли фото лица.",
        reply_markup=generate_or_photo_keyboard(),
    )
