from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.exceptions import AppError, Conflict, NotFound
from app.models import Category, User, UserRole
from app.schemas import CategoryCreate, CategoryUpdate


async def get_categories(session: AsyncSession) -> list[Category]:
    stmt = select(Category).options(selectinload(Category.responsible_user)).order_by(Category.id.desc())
    return list(await session.scalars(stmt))


async def get_category(session: AsyncSession, category_id: int) -> Category:
    stmt = select(Category).options(selectinload(Category.responsible_user)).where(Category.id == category_id)
    category = await session.scalar(stmt)
    if not category:
        raise NotFound("Category not found")
    return category


async def check_category_name_exist(session: AsyncSession, name: str) -> None:
    if await session.scalar(select(Category.id).where(Category.name == name)):
        raise Conflict("Category with this name already exists")


async def check_responsible_user_status(session: AsyncSession, user_id: int) -> None:
    user = await session.get(User, user_id)
    if not user or not user.is_active or user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise AppError("Responsible user must be an active manager or admin")


async def create_category(session: AsyncSession, data: CategoryCreate) -> Category:
    await check_category_name_exist(session, data.name)
    await check_responsible_user_status(session, data.responsible_user_id)

    category = Category(name=data.name, responsible_user_id=data.responsible_user_id)
    session.add(category)
    await session.commit()
    await session.refresh(category, ["responsible_user"])
    return category


async def update_category(session: AsyncSession, category_id: int, data: CategoryUpdate) -> Category:
    category = await get_category(session, category_id)

    if data.name is not None and data.name != category.name:
        await check_category_name_exist(session, data.name)
        category.name = data.name
    if data.responsible_user_id is not None:
        await check_responsible_user_status(session, data.responsible_user_id)
        category.responsible_user_id = data.responsible_user_id

    await session.commit()
    # Reload the relation, otherwise the response could show the previous responsible user.
    await session.refresh(category, ["responsible_user"])
    return category
