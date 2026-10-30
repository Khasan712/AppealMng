from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.exceptions import NotFound, AppError, Conflict
from app.models import Appeal, AppealSource, AppealStatus, AppealStatusHistory, Category, User, UserRole
from app.schemas import AppealCreate
from app.services.categories import get_category
from app.services import notifications as notification_service


# Allowed workflow transitions. CLOSED and REJECTED are final.
ALLOWED_APPEAL_STATUSES = {
    AppealStatus.NEW: {AppealStatus.IN_PROGRESS, AppealStatus.REJECTED},
    AppealStatus.IN_PROGRESS: {AppealStatus.CLOSED, AppealStatus.REJECTED},
}


def with_relations(stmt: Select) -> Select:
    return stmt.options(
        selectinload(Appeal.category).selectinload(Category.responsible_user),
        selectinload(Appeal.author),
    )


# Appealers see their own appeals, managers see appeals of their categories, admins see all.
def visible_to(stmt: Select, user: User) -> Select:
    if user.role == UserRole.APPEALER:
        return stmt.where(Appeal.author_id == user.id)
    if user.role == UserRole.MANAGER:
        return stmt.join(Appeal.category).where(Category.responsible_user_id == user.id)
    return stmt


async def create_appeal(
    session: AsyncSession, data: AppealCreate, author: User, source: AppealSource = AppealSource.WEB
) -> Appeal:
    await get_category(session, data.category_id)

    appeal = Appeal(
        phone=data.phone,
        description=data.description,
        category_id=data.category_id,
        author_id=author.id,
        status=AppealStatus.NEW,
        source=source,
    )
    # First history record, so the history covers the whole life of the appeal.
    appeal.history.append(AppealStatusHistory(updated_by_id=author.id, new_status=AppealStatus.NEW))
    session.add(appeal)
    await session.commit()
    return await get_appeal(session, appeal.id, author)


def detail_query(appeal_id: int) -> Select:
    return (
        with_relations(select(Appeal))
        .options(selectinload(Appeal.history).selectinload(AppealStatusHistory.updated_by))
        .where(Appeal.id == appeal_id)
        # Refresh objects already loaded in this session, e.g. right after a status change.
        .execution_options(populate_existing=True)
    )


async def get_appeal(session: AsyncSession, appeal_id: int, user: User, for_update: bool = False) -> Appeal:
    stmt = visible_to(detail_query(appeal_id), user)
    # Row lock: two concurrent actions cannot both change the same appeal.
    if for_update:
        stmt = stmt.with_for_update(of=Appeal)
    appeal = await session.scalar(stmt)
    if not appeal:
        raise NotFound("Appeal not found")
    return appeal


async def get_appeals_list(
    session: AsyncSession,
    user: User,
    status: AppealStatus | None = None,
    category_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Appeal]:
    stmt = visible_to(with_relations(select(Appeal)), user)
    if status:
        stmt = stmt.where(Appeal.status == status)
    if category_id:
        stmt = stmt.where(Appeal.category_id == category_id)
    stmt = stmt.order_by(Appeal.created_at.desc()).limit(limit).offset(offset)
    return list(await session.scalars(stmt))


async def change_status(
    session: AsyncSession, appeal_id: int, user: User, new_status: AppealStatus, comment: str | None = None
) -> Appeal:
    appeal = await get_appeal(session, appeal_id, user, for_update=True)
    if new_status not in ALLOWED_APPEAL_STATUSES.get(appeal.status, set()):
        raise Conflict(f"Cannot change status from {appeal.status.value} to {new_status.value}")

    previous_status = appeal.status
    appeal.status = new_status
    session.add(AppealStatusHistory(
        appeal_id=appeal.id,
        updated_by_id=user.id,
        previous_status=previous_status,
        new_status=new_status,
        comment=comment,
    ))
    notification = notification_service.notify_status_change(session, appeal, comment)
    await session.commit()
    # Send only after commit, so nobody is notified about a change that was rolled back.
    await notification_service.send_to_telegram(session, notification, appeal.author.telegram_id)
    return await session.scalar(detail_query(appeal_id))


async def change_category(
    session: AsyncSession, appeal_id: int, user: User, category_id: int, comment: str | None = None
) -> Appeal:
    appeal = await get_appeal(session, appeal_id, user, for_update=True)
    if appeal.status != AppealStatus.NEW:
        raise Conflict("Category can only be changed for new appeals")

    new_category = await get_category(session, category_id)
    if new_category.id == appeal.category_id:
        raise AppError("Appeal is already in this category")

    note = f"Category changed: {appeal.category.name} → {new_category.name}"
    if comment:
        note += f". {comment}"

    appeal.category_id = new_category.id
    session.add(AppealStatusHistory(
        appeal_id=appeal.id,
        updated_by_id=user.id,
        previous_status=appeal.status,
        new_status=appeal.status,  # not a status change, kept in history for audit
        comment=note,
    ))
    await session.commit()
    return await session.scalar(detail_query(appeal_id))