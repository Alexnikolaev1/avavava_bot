from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.jobs import offer_confirm
from bot.keyboards import (
    CB_I2V,
    CB_I2V_DUR,
    CB_VOICE,
    CB_VOICE_LANG,
    hub_video_keyboard,
    hub_voice_keyboard,
    i2v_duration_keyboard,
    voice_language_keyboard,
)
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_i2v, estimate_voice_tts
from bot.states import I2VFlow, VoiceFlow
from bot.texts import I2V_PROMPT, I2V_SEND_PHOTO, VOICE_SAMPLE, VOICE_TEXT

router = Router()


@router.callback_query(F.data == CB_I2V)
async def cb_i2v(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(I2VFlow.waiting_for_photo)
    await callback.message.answer(I2V_SEND_PHOTO)
    await callback.answer()


@router.message(Command("i2v"))
async def cmd_i2v(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(I2VFlow.waiting_for_photo)
    await message.answer(I2V_SEND_PHOTO)


@router.message(StateFilter(I2VFlow.waiting_for_photo), F.photo)
async def i2v_photo(message: Message, state: FSMContext) -> None:
    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await state.set_state(I2VFlow.waiting_for_prompt)
    await message.answer(I2V_PROMPT)


@router.message(StateFilter(I2VFlow.waiting_for_prompt), F.text)
async def i2v_prompt(message: Message, state: FSMContext) -> None:
    prompt = (message.text or "").strip()
    if len(prompt) < 5:
        await message.answer("Промпт слишком короткий.")
        return
    await state.update_data(prompt=prompt)
    await state.set_state(I2VFlow.choosing_duration)
    await message.answer("Длительность видео:", reply_markup=i2v_duration_keyboard())


@router.callback_query(StateFilter(I2VFlow.choosing_duration), F.data.startswith(CB_I2V_DUR))
async def i2v_duration(
    callback: CallbackQuery,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    duration = int(callback.data.removeprefix(CB_I2V_DUR))
    data = await state.get_data()
    await state.clear()
    cost = estimate_i2v(duration)
    await offer_confirm(
        callback.message,
        pending,
        callback.from_user.id,
        "i2v",
        {
            "photo_file_id": data["photo_file_id"],
            "prompt": data["prompt"],
            "duration": duration,
        },
        cost,
    )
    await callback.answer()


@router.callback_query(F.data == CB_VOICE)
async def cb_voice(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(VoiceFlow.waiting_for_sample)
    await callback.message.answer(VOICE_SAMPLE)
    await callback.answer()


@router.message(Command("voice"))
async def cmd_voice(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(VoiceFlow.waiting_for_sample)
    await message.answer(VOICE_SAMPLE)


@router.message(StateFilter(VoiceFlow.waiting_for_sample), F.voice | F.audio)
async def voice_sample(message: Message, state: FSMContext) -> None:
    audio = message.voice or message.audio
    if audio.duration and audio.duration < 6:
        await message.answer("Нужно минимум 6 секунд образца голоса для клонирования.")
        return
    await state.update_data(sample_file_id=audio.file_id)
    await state.set_state(VoiceFlow.choosing_language)
    await message.answer("Выбери язык озвучки:", reply_markup=voice_language_keyboard())


@router.callback_query(StateFilter(VoiceFlow.choosing_language), F.data.startswith(CB_VOICE_LANG))
async def voice_lang(callback: CallbackQuery, state: FSMContext) -> None:
    lang = callback.data.removeprefix(CB_VOICE_LANG)
    await state.update_data(language=lang)
    await state.set_state(VoiceFlow.waiting_for_text)
    await callback.message.answer(VOICE_TEXT)
    await callback.answer()


@router.message(StateFilter(VoiceFlow.waiting_for_text), F.text)
async def voice_text(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("Текст слишком короткий.")
        return
    data = await state.get_data()
    await state.clear()
    cost = estimate_voice_tts()
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "voice",
        {
            "sample_file_id": data["sample_file_id"],
            "text": text,
            "language": data.get("language", "ru"),
        },
        cost,
    )
