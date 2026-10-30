import asyncio
import logging
from aiogram import Bot, Dispatcher
from app.config import settings
from bot.handlers import router


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = Bot(settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
