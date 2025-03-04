import logging

from typing import Callable, Awaitable, Dict, Any


from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from cachetools import TTLCache
from sqlalchemy import select


from ..database.models import User
from ..database.engine import session_maker


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Считывает каждое взаимодействие пользователей с ботом и обрабатывает ошибки"""
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        logger.info(f'User "{event.from_user.username}" ({event.from_user.id}) '
                    f'отправил: {event.text if isinstance(event, Message) else event.data}')

        try:
            return await handler(event, data)
        except Exception as e:
            logger.exception(f"Возникла ошибка при обработке {event.from_user.id}: {e}")
            raise e


class UserMiddleware(BaseMiddleware):
    """Проверяет находиться ли пользователь в базе данных, если нет то добавляет"""

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        async with session_maker() as session:
            user = await session.scalar(select(User).where(User.telegram_id == event.from_user.id))
            try:
                if not user:
                    user = User(
                        telegram_id=event.from_user.id,
                        name=event.from_user.full_name,
                        username=event.from_user.username,
                        phone='не указан'
                    )
                    session.add(user)
                    await session.commit()

                data['user'] = user
                return await handler(event, data)

            except Exception as e:
                raise e



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