import os
from typing import List

from dotenv import load_dotenv
from aiogram.filters import Filter
from aiogram.types import Message

load_dotenv()

class AdminChecker(Filter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
      return str(message.from_user.id) in os.getenv('ADMIN')
