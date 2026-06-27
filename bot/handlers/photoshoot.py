from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.jobs import offer_confirm
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_photoshoot
from bot.keyboards import (
    CB_PHOTOSHOOT,
    CB_PS_DEFAULT_PROMPT,
    CB_PS_FTM,
    CB_PS_GENDER,
    CB_PS_BG,
    CB_PS_PHOTOS_DONE,
    CB_PS_PM,
    CB_PS_PRESET,
    CB_PS_RESTART,
    ftm_styles_keyboard,
    headshot_background_keyboard,
    headshot_gender_keyboard,
    main_menu_keyboard,
    photomaker_styles_keyboard,
    photoshoot_photos_done_keyboard,
    photoshoot_presets_keyboard,
)
from bot.photoshoot_catalog import CUSTOM_PROMPT_HINTS, PRESETS
from bot.states import PhotoshootFlow
from bot.texts import (
    PHOTOSHOOT_CHOOSE_ART,
    PHOTOSHOOT_CHOOSE_BG,
    PHOTOSHOOT_CHOOSE_GENDER,
    PHOTOSHOOT_CHOOSE_PM_STYLE,
    PHOTOSHOOT_SEND_PHOTO,
    PHOTOSHOOT_SEND_PHOTOS,
    PHOTOSHOOT_START,
)

router = Router()


async def _start_photoshoot(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(PhotoshootFlow.choosing_preset)
    await message.answer(PHOTOSHOOT_START, reply_markup=photoshoot_presets_keyboard())


@router.callback_query(F.data == CB_PHOTOSHOOT)
async def cb_photoshoot(callback: CallbackQuery, state: FSMContext) -> None:
    await _start_photoshoot(callback.message, state)
    await callback.answer()


@router.message(Command("photoshoot"))
async def cmd_photoshoot(message: Message, state: FSMContext) -> None:
    await _start_photoshoot(message, state)


@router.callback_query(
    StateFilter(PhotoshootFlow.choosing_preset),
    F.data.startswith(CB_PS_PRESET),
)
async def cb_choose_preset(callback: CallbackQuery, state: FSMContext) -> None:
    preset_key = callback.data.removeprefix(CB_PS_PRESET)
    preset = PRESETS.get(preset_key)
    if not preset:
        await callback.answer("Неизвестный формат", show_alert=True)
        return

    await state.update_data(preset=preset_key, photo_file_ids=[])
    await state.set_state(PhotoshootFlow.waiting_for_photos)
    text = PHOTOSHOOT_SEND_PHOTOS if preset_key == "custom" else PHOTOSHOOT_SEND_PHOTO
    markup = photoshoot_photos_done_keyboard(0) if preset_key == "custom" else None
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == CB_PS_RESTART)
async def cb_photoshoot_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(
        "Фотосессия отменена. Главное меню 👇",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(PhotoshootFlow.waiting_for_photos), F.photo)
async def receive_photoshoot_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    preset = data.get("preset", "official")
    photos: list[str] = list(data.get("photo_file_ids") or [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photo_file_ids=photos)

    if preset == "official":
        await state.set_state(PhotoshootFlow.choosing_background)
        await message.answer(PHOTOSHOOT_CHOOSE_BG, reply_markup=headshot_background_keyboard())
        return

    if preset == "art":
        await state.set_state(PhotoshootFlow.choosing_art_style)
        await message.answer(PHOTOSHOOT_CHOOSE_ART, reply_markup=ftm_styles_keyboard())
        return

    max_photos = PRESETS["custom"].max_photos
    if len(photos) >= max_photos:
        await message.answer(
            f"Принято {max_photos} фото — нажми «Готово» для продолжения.",
            reply_markup=photoshoot_photos_done_keyboard(len(photos)),
        )
        return

    await message.answer(
        f"Фото {len(photos)}/{max_photos}. Можно добавить ещё или нажать «Готово».",
        reply_markup=photoshoot_photos_done_keyboard(len(photos)),
    )


@router.callback_query(
    StateFilter(PhotoshootFlow.waiting_for_photos),
    F.data == CB_PS_PHOTOS_DONE,
)
async def cb_photos_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photo_file_ids") or [])
    if not photos:
        await callback.answer("Сначала пришли хотя бы одно фото", show_alert=True)
        return

    await state.set_state(PhotoshootFlow.choosing_pm_style)
    await callback.message.answer(
        PHOTOSHOOT_CHOOSE_PM_STYLE,
        reply_markup=photomaker_styles_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(PhotoshootFlow.waiting_for_photos))
async def wrong_photoshoot_photo(message: Message) -> None:
    await message.answer("Жду фото (как изображение, не документ).")


@router.callback_query(
    StateFilter(PhotoshootFlow.choosing_background),
    F.data.startswith(CB_PS_BG),
)
async def cb_choose_background(callback: CallbackQuery, state: FSMContext) -> None:
    background = callback.data.removeprefix(CB_PS_BG)
    await state.update_data(background=background)
    await state.set_state(PhotoshootFlow.choosing_gender)
    await callback.message.answer(PHOTOSHOOT_CHOOSE_GENDER, reply_markup=headshot_gender_keyboard())
    await callback.answer()


@router.callback_query(
    StateFilter(PhotoshootFlow.choosing_gender),
    F.data.startswith(CB_PS_GENDER),
)
async def cb_choose_gender(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    gender = callback.data.removeprefix(CB_PS_GENDER)
    await state.update_data(gender=None if gender == "skip" else gender)
    await _launch_generation(callback.message, state, settings, pending, callback.from_user.id)
    await callback.answer()


@router.callback_query(
    StateFilter(PhotoshootFlow.choosing_art_style),
    F.data.startswith(CB_PS_FTM),
)
async def cb_choose_art_style(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    style_key = callback.data.removeprefix(CB_PS_FTM)
    await state.update_data(ftm_style_key=style_key)
    await _launch_generation(callback.message, state, settings, pending, callback.from_user.id)
    await callback.answer()


@router.callback_query(
    StateFilter(PhotoshootFlow.choosing_pm_style),
    F.data.startswith(CB_PS_PM),
)
async def cb_choose_pm_style(callback: CallbackQuery, state: FSMContext) -> None:
    style_key = callback.data.removeprefix(CB_PS_PM)
    await state.update_data(pm_style_key=style_key)
    await state.set_state(PhotoshootFlow.waiting_custom_prompt)
    await callback.message.answer(
        f"Напиши промпт для фотосессии.\n\n{CUSTOM_PROMPT_HINTS}",
        reply_markup=_default_prompt_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(PhotoshootFlow.waiting_custom_prompt),
    F.data == CB_PS_DEFAULT_PROMPT,
)
async def cb_default_prompt(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    await state.update_data(custom_prompt="a photo of a person img, professional studio portrait")
    await _launch_generation(callback.message, state, settings, pending, callback.from_user.id)
    await callback.answer()


@router.message(StateFilter(PhotoshootFlow.waiting_custom_prompt), F.text)
async def receive_custom_prompt(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
) -> None:
    prompt = (message.text or "").strip()
    if len(prompt) < 5:
        await message.answer("Промпт слишком короткий. Опиши образ подробнее.")
        return
    await state.update_data(custom_prompt=prompt)
    await _launch_generation(message, state, settings, pending, message.from_user.id)


@router.message(StateFilter(PhotoshootFlow.waiting_custom_prompt))
async def wrong_custom_prompt(message: Message) -> None:
    await message.answer("Жду текстовый промпт или нажми «Стандартный промпт».")


def _default_prompt_keyboard():
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✨ Стандартный промпт",
                    callback_data=CB_PS_DEFAULT_PROMPT,
                )
            ]
        ]
    )


async def _launch_generation(
    message: Message,
    state: FSMContext,
    settings: Settings,
    pending: PendingStore,
    user_id: int,
) -> None:
    data = await state.get_data()
    photos: list[str] = list(data.get("photo_file_ids") or [])
    if not photos:
        await message.answer("Нет фото. Начни заново: /photoshoot")
        await state.clear()
        return

    preset = data.get("preset", "official")
    cost = estimate_photoshoot(preset)
    payload = {
        "preset": preset,
        "photo_file_ids": photos,
        "gender": data.get("gender"),
        "background": data.get("background", "neutral"),
        "ftm_style_key": data.get("ftm_style_key", "3d"),
        "pm_style_key": data.get("pm_style_key", "photo"),
        "custom_prompt": data.get("custom_prompt"),
    }
    await state.clear()
    await offer_confirm(message, pending, user_id, "photoshoot", payload, cost)
