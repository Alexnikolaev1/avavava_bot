from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import Settings

log = logging.getLogger(__name__)


class AccessMiddleware(BaseMiddleware):
    """Пропускает только пользователей из ALLOWED_USER_IDS (если список задан)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        settings: Settings = data["settings"]
        user_id = _extract_user_id(event)
        if user_id is None:
            return await handler(event, data)

        if settings.is_user_allowed(user_id):
            return await handler(event, data)

        log.warning("Access denied user_id=%s", user_id)
        if isinstance(event, Message):
            await event.answer(
                "Бот закрыт — доступ только для авторизованных пользователей.\n\n"
                f"Твой Telegram ID: <code>{user_id}</code>\n"
                "Добавь его в переменную <code>ALLOWED_USER_IDS</code> на сервере."
            )
        elif isinstance(event, CallbackQuery):
            await event.answer("Нет доступа к этому боту.", show_alert=True)
        return None


def _extract_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user.id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None
