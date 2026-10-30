from aiogram import Bot

from app.config import settings

# Send-only client for notifications; polling runs in the bot service.
tg_bot = Bot(settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else None
