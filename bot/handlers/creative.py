from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.jobs import offer_confirm
from bot.keyboards import (
    CB_RESTORE,
    CB_RESTORE_MODE,
    CB_SCENE,
    CB_SCENE_PRESET,
    CB_SCENE_TYPE,
    hub_photo_keyboard,
    restore_modes_keyboard,
    scene_presets_keyboard,
    scene_type_keyboard,
)
from bot.services.pending import PendingStore
from bot.services.pricing import estimate_restore, estimate_scene
from bot.states import RestoreFlow, SceneFlow
from bot.texts import RESTORE_START, SCENE_CHOOSE_PRESET, SCENE_CHOOSE_TYPE, SCENE_SEND_PHOTO

router = Router()


@router.callback_query(F.data == CB_RESTORE)
async def cb_restore(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RestoreFlow.choosing_mode)
    await callback.message.answer(RESTORE_START, reply_markup=restore_modes_keyboard())
    await callback.answer()


@router.message(Command("restore"))
async def cmd_restore(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RestoreFlow.choosing_mode)
    await message.answer(RESTORE_START, reply_markup=restore_modes_keyboard())


@router.callback_query(StateFilter(RestoreFlow.choosing_mode), F.data.startswith(CB_RESTORE_MODE))
async def cb_restore_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.removeprefix(CB_RESTORE_MODE)
    await state.update_data(restore_mode=mode)
    await state.set_state(RestoreFlow.waiting_for_photo)
    await callback.message.answer("Пришли старое или повреждённое фото.")
    await callback.answer()


@router.message(StateFilter(RestoreFlow.waiting_for_photo), F.photo)
async def restore_photo(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    data = await state.get_data()
    mode = data.get("restore_mode", "restore")
    await state.clear()
    cost = estimate_restore(upscale=mode != "restore")
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "restore",
        {"photo_file_id": message.photo[-1].file_id, "mode": mode},
        cost,
    )


@router.callback_query(F.data == CB_SCENE)
async def cb_scene(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SceneFlow.choosing_type)
    await callback.message.answer(SCENE_CHOOSE_TYPE, reply_markup=scene_type_keyboard())
    await callback.answer()


@router.message(Command("scene"))
async def cmd_scene(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SceneFlow.choosing_type)
    await message.answer(SCENE_CHOOSE_TYPE, reply_markup=scene_type_keyboard())


@router.callback_query(StateFilter(SceneFlow.choosing_type), F.data.startswith(CB_SCENE_TYPE))
async def cb_scene_type(callback: CallbackQuery, state: FSMContext) -> None:
    scene_type = callback.data.removeprefix(CB_SCENE_TYPE)
    await state.update_data(scene_type=scene_type)
    await state.set_state(SceneFlow.choosing_preset)
    await callback.message.answer(
        SCENE_CHOOSE_PRESET,
        reply_markup=scene_presets_keyboard(scene_type),
    )
    await callback.answer()


@router.callback_query(StateFilter(SceneFlow.choosing_preset), F.data.startswith(CB_SCENE_PRESET))
async def cb_scene_preset(callback: CallbackQuery, state: FSMContext) -> None:
    preset = callback.data.removeprefix(CB_SCENE_PRESET)
    await state.update_data(scene_key=preset)
    await state.set_state(SceneFlow.waiting_for_photo)
    await callback.message.answer(SCENE_SEND_PHOTO)
    await callback.answer()


@router.message(StateFilter(SceneFlow.waiting_for_photo), F.photo)
async def scene_photo(
    message: Message,
    state: FSMContext,
    pending: PendingStore,
) -> None:
    data = await state.get_data()
    scene_type = data.get("scene_type", "iconic")
    await state.clear()
    cost = estimate_scene(scene_type)
    await offer_confirm(
        message,
        pending,
        message.from_user.id,
        "scene",
        {
            "photo_file_id": message.photo[-1].file_id,
            "scene_type": scene_type,
            "scene_key": data.get("scene_key", "eiffel"),
        },
        cost,
    )
