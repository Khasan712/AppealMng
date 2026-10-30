from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.exceptions import Conflict, Unauthorized
from app.models import User, UserRole
from app.schemas import UserRegister, normalize_phone
from app.security import hash_password, verify_password


async def get_by_phone(session: AsyncSession, phone: str) -> User | None:
    return await session.scalar(select(User).where(User.phone == phone))


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def create_user(session: AsyncSession, data: UserRegister, role: UserRole = UserRole.APPEALER) -> User:
    user = await get_by_phone(session, data.phone)
    if user and user.hashed_password:
        raise Conflict("User with this phone already exists")

    if user:
        # Created via Telegram without a password: let the owner set one for web access.
        user.hashed_password = hash_password(data.password)
        user.full_name = user.full_name or data.full_name
    else:
        user = User(
            phone=data.phone,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=role,
        )
        session.add(user)

    await session.commit()
    await session.refresh(user)
    return user


async def authenticate(session: AsyncSession, phone: str, password: str) -> User:
    try:
        phone = normalize_phone(phone)
    except ValueError:
        raise Unauthorized("Incorrect phone or password")
    user = await get_by_phone(session, phone)
    # Same message for unknown phone and wrong password, so registered numbers cannot be guessed.
    if not user or not verify_password(password, user.hashed_password):
        raise Unauthorized("Incorrect phone or password")
    if not user.is_active:
        raise Unauthorized("User is inactive")
    return user


async def get_users_list(session: AsyncSession, role: UserRole | None = None) -> list[User]:
    stmt = select(User).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    return list(await session.scalars(stmt))


# The phone comes from the user's own Telegram contact, so it is safe to link it to an existing account.
async def link_telegram(session: AsyncSession, phone: str, telegram_id: int, full_name: str | None) -> User:
    user = await get_by_phone(session, phone)
    if user and user.telegram_id and user.telegram_id != telegram_id:
        raise Conflict("This phone number is already linked to another Telegram account")

    if user:
        user.telegram_id = telegram_id
        user.full_name = user.full_name or full_name
    else:
        user = User(phone=phone, full_name=full_name, telegram_id=telegram_id, role=UserRole.APPEALER)
        session.add(user)

    await session.commit()
    await session.refresh(user)
    return user
