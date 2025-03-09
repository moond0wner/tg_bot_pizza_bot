from typing import Callable, Awaitable, Dict, Any

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from cachetools import TTLCache

from ..database.requests import is_user_exists, add_user
from .logger import Logger

class UserMiddleware(BaseMiddleware):
    """
    Проверяет находиться ли пользователь в базе данных, если нет то добавляет
    """

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        if not await is_user_exists(event.from_user.id):
            await add_user(user_id=event.from_user.id, name=event.from_user.full_name,
                           username=event.from_user.username)

            Logger.info(f'Пользователь {event.from_user.id} успешно зарегистрирован!')

        return await handler(event, data)



class ThrottlingMiddleware(BaseMiddleware):
    """Уменьшает частоту обработки сообщений при спаме
    Если пользователь флудит /start или inline кнопками,
    то в течение 1 секунды запросы не обрабатываются"""
    def __init__(self, time_limit: int=1) -> None:
        self.limit = TTLCache(maxsize=10_000, ttl=time_limit)


    async def __call__(
            self,
            handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str,  Any]
    ) -> Any:
        if event.from_user.id in self.limit:
            await event.answer("Пожалуйста, не флудите!")
            return
        else:
            self.limit[event.from_user.id] = None
        return await handler(event, data)