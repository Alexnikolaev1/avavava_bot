from __future__ import annotations

import asyncio

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import Settings
from bot.handlers.common import check_cooldown, show_favorites_list
from bot.keyboards import (
    CB_FAV_DEL,
    CB_FAV_DANCE,
    CB_FAV_LIST,
    CB_FAV_NAME_AUTO,
    CB_FAV_SAVE,
    CB_FAV_USE,
    avatar_actions_keyboard,
    favorite_name_keyboard,
)
from bot.models.avatar_config import AvatarConfig
from bot.services.favorites import FavoritesStore
from bot.services.pipeline import GenerationPipeline
from bot.states import AvatarFlow, MotionFlow
from bot.texts import (
    FAV_ASK_NAME,
    FAV_DELETED,
    FAV_LIMIT,
    FAV_LOADED,
    FAV_SAVED,
    MOTION_SEND_VIDEO,
    STATUS,
    avatar_ready_text,
)

router = Router()


async def _save_favorite(
    *,
    user_id: int,
    name: str,
    avatar_file_id: str,
    config: AvatarConfig,
    favorites: FavoritesStore,
    settings: Settings,
    reply: Message,
) -> None:
    saved = await favorites.add(user_id, name, avatar_file_id, config)
    if saved is None:
        await reply.answer(
            FAV_LIMIT.format(limit=settings.max_favorites_per_user)
        )
        return
    await reply.answer(FAV_SAVED.format(name=saved.name))


@router.message(Command("favorites"))
async def cmd_favorites(message: Message, favorites: FavoritesStore) -> None:
    await show_favorites_list(message, favorites, message.from_user.id)


@router.callback_query(F.data == CB_FAV_LIST)
async def cb_favorites_list(callback: CallbackQuery, favorites: FavoritesStore) -> None:
    await show_favorites_list(callback.message, favorites, callback.from_user.id, edit=True)
    await callback.answer()


@router.callback_query(F.data == CB_FAV_SAVE)
async def cb_fav_save(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    avatar_file_id = data.get("avatar_file_id")
    if not avatar_file_id:
        await callback.answer("Сначала создай персонажа", show_alert=True)
        return

    config = AvatarConfig.from_fsm(data)
    suggested = config.auto_name()
    await state.update_data(fav_suggested_name=suggested)
    await state.set_state(AvatarFlow.naming_favorite)
    await callback.message.answer(
        FAV_ASK_NAME,
        reply_markup=favorite_name_keyboard(suggested),
    )
    await callback.answer()


@router.callback_query(StateFilter(AvatarFlow.naming_favorite), F.data == CB_FAV_NAME_AUTO)
async def cb_fav_name_auto(
    callback: CallbackQuery,
    state: FSMContext,
    favorites: FavoritesStore,
    settings: Settings,
) -> None:
    data = await state.get_data()
    name = data.get("fav_suggested_name") or AvatarConfig.from_fsm(data).auto_name()
    avatar_file_id = data.get("avatar_file_id")
    if not avatar_file_id:
        await callback.answer("Персонаж не найден", show_alert=True)
        await state.set_state(AvatarFlow.waiting_for_audio)
        return

    config = AvatarConfig.from_fsm(data)
    await _save_favorite(
        user_id=callback.from_user.id,
        name=name,
        avatar_file_id=avatar_file_id,
        config=config,
        favorites=favorites,
        settings=settings,
        reply=callback.message,
    )
    await state.set_state(AvatarFlow.waiting_for_audio)
    await callback.answer("Сохранено!")


@router.message(StateFilter(AvatarFlow.naming_favorite), F.text)
async def fav_name_text(
    message: Message,
    state: FSMContext,
    favorites: FavoritesStore,
    settings: Settings,
) -> None:
    name = (message.text or "").strip()
    if len(name) < 1:
        await message.answer("Имя не может быть пустым.")
        return
    if len(name) > 64:
        await message.answer("Имя слишком длинное — максимум 64 символа.")
        return

    data = await state.get_data()
    avatar_file_id = data.get("avatar_file_id")
    if not avatar_file_id:
        await message.answer("Персонаж не найден. /start")
        await state.clear()
        return

    config = AvatarConfig.from_fsm(data)
    await _save_favorite(
        user_id=message.from_user.id,
        name=name,
        avatar_file_id=avatar_file_id,
        config=config,
        favorites=favorites,
        settings=settings,
        reply=message,
    )
    await state.set_state(AvatarFlow.waiting_for_audio)


@router.callback_query(F.data.startswith(CB_FAV_DEL))
async def cb_fav_delete(callback: CallbackQuery, favorites: FavoritesStore) -> None:
    fav_id = int(callback.data.removeprefix(CB_FAV_DEL))
    deleted = await favorites.delete(callback.from_user.id, fav_id)
    if deleted:
        await callback.answer("Удалено")
        await show_favorites_list(callback.message, favorites, callback.from_user.id, edit=True)
    else:
        await callback.answer("Не найдено", show_alert=True)


@router.callback_query(F.data.startswith(CB_FAV_DANCE))
async def cb_fav_dance(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    favorites: FavoritesStore,
) -> None:
    fav_id = int(callback.data.removeprefix(CB_FAV_DANCE))
    favorite = await favorites.get(callback.from_user.id, fav_id)
    if not favorite:
        await callback.answer("Персонаж не найден", show_alert=True)
        return
    await state.clear()
    await state.update_data(
        mode="kling",
        photo_file_id=favorite.avatar_file_id,
        pipeline_photo=True,
    )
    await state.set_state(MotionFlow.waiting_for_video)
    await callback.message.answer(
        f"💃 Персонаж «{favorite.name}» выбран.\n"
        + MOTION_SEND_VIDEO.format(max_seconds=settings.motion_max_video_seconds)
    )
    await callback.answer()


@router.callback_query(F.data.startswith(CB_FAV_USE))
async def cb_fav_use(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    pipeline: GenerationPipeline,
    favorites: FavoritesStore,
) -> None:
    fav_id = int(callback.data.removeprefix(CB_FAV_USE))
    favorite = await favorites.get(callback.from_user.id, fav_id)
    if not favorite:
        await callback.answer("Персонаж не найден", show_alert=True)
        return

    await state.clear()
    config = favorite.config
    config.source = "favorite"
    avatar_file_id = favorite.avatar_file_id

    try:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=avatar_file_id,
            caption=f"⭐ {favorite.name}",
        )
    except TelegramBadRequest:
        await callback.answer("Обновляю изображение...", show_alert=False)
        status = await callback.message.answer(STATUS["regenerating_fav"])
        new_file_id = await pipeline.regenerate_from_config(
            callback.message.chat.id,
            config,
            status_message_id=status.message_id,
        )
        if not new_file_id:
            await callback.answer("Не удалось восстановить персонажа", show_alert=True)
            return
        avatar_file_id = new_file_id
        await favorites.update_file_id(fav_id, new_file_id)

    await state.update_data(
        avatar_file_id=avatar_file_id,
        animal_key=config.animal_key,
        custom_animal=config.custom_animal,
        style_key=config.style_key,
        gender_key=config.gender_key,
        emotion_key=config.emotion_key,
        source=config.source,
        favorite_id=fav_id,
    )
    await state.set_state(AvatarFlow.waiting_for_audio)
    await callback.message.answer(
        FAV_LOADED.format(name=favorite.name),
        reply_markup=avatar_actions_keyboard(can_save=False),
    )
    await callback.answer()
