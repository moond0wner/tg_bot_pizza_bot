import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from dotenv import load_dotenv

from src.handlers.admin import admin
from src.handlers.user import user
from src.database.engine import create_db
from src.utils.middlewares import LoggingMiddleware, UserMiddleware, ThrottlingMiddleware

load_dotenv()


async def main():
    os.makedirs('images', exist_ok=True)

    bot = Bot(token=os.getenv('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.message.middleware(UserMiddleware())

    dp.include_routers(user, admin)

    await create_db()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass