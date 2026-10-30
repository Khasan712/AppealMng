from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Appeal, AppealStatus, AppealStatusHistory, Category


async def get_stats_list(session: AsyncSession) -> dict:
    status_rows = await session.execute(select(Appeal.status, func.count()).group_by(Appeal.status))
    by_status = {s: 0 for s in AppealStatus}  # statuses without appeals are shown as 0
    by_status.update(dict(status_rows.all()))

    category_rows = await session.execute(
        select(Category.id, Category.name, func.count(Appeal.id))
        .outerjoin(Appeal, Appeal.category_id == Category.id)
        .group_by(Category.id)
        .order_by(func.count(Appeal.id).desc())
    )
    by_category = [{"category_id": cid, "name": name, "count": count} for cid, name, count in category_rows]

    # Counted from history: an appeal stays "accepted" even after it is closed or rejected.
    accepted = await session.scalar(
        select(func.count(func.distinct(AppealStatusHistory.appeal_id)))
        .where(AppealStatusHistory.new_status == AppealStatus.IN_PROGRESS)
    )

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_category": by_category,
        "accepted": accepted,
        "rejected": by_status[AppealStatus.REJECTED],
        "closed": by_status[AppealStatus.CLOSED],
    }
