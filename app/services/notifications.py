import logging

from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appeal, Notification, User
from app.telegram import tg_bot

logger = logging.getLogger(__name__)


def notify_status_change(session: AsyncSession, appeal: Appeal, comment: str | None) -> Notification:
    message = f"Appeal #{appeal.id}: status changed to {appeal.status.value}."
    if comment:
        message += f" Comment: {comment}"
    notification = Notification(user_id=appeal.author_id, appeal_id=appeal.id, message=message)
    session.add(notification)
    return notification


async def send_to_telegram(session: AsyncSession, notification: Notification, telegram_id: int | None) -> None:
    if not tg_bot or not telegram_id:
        return
    try:
        await tg_bot.send_message(telegram_id, f"🔔 {notification.message}", request_timeout=5)
    # A delivery failure must not fail the status change; the notification is still shown on the web.
    except TelegramAPIError as e:
        logger.warning("Telegram notification %s was not delivered: %s", notification.id, e)
        return
    notification.is_sent = True
    await session.commit()


async def get_notifications_list(session: AsyncSession, user: User, limit: int = 50) -> list[Notification]:
    stmt = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(await session.scalars(stmt))