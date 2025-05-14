from aiogram import BaseMiddleware, types
from typing import Callable, Awaitable, Dict, Any
from config import Config

class AccessMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None

        if isinstance(event, types.Message):
            user_id = event.from_user.id
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id

        if user_id is not None and user_id not in Config.ALLOWED_USERS:
            if isinstance(event, types.Message):
                await event.answer("⛔ Доступ запрещён!")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("⛔ Доступ запрещён!", show_alert=True)
            return

        return await handler(event, data)
