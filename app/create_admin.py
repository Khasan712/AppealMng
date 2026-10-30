"""Create an administrator: python -m app.create_admin --phone +998XXXXXXXXX --name "Admin"."""
import argparse
import asyncio
from getpass import getpass
from pydantic import ValidationError
from app.database import Base, SessionLocal, engine
from app.exceptions import AppError
from app.models import UserRole
from app.schemas import UserCreate
from app.services.users import create_user


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create an administrator account")
    parser.add_argument("--phone", required=True)
    parser.add_argument("--name")
    args = parser.parse_args()
    password = getpass("Password: ")

    try:
        data = UserCreate(phone=args.phone, password=password, full_name=args.name, role=UserRole.ADMIN)
    except ValidationError as e:
        raise SystemExit(f"Invalid data: {e}")

    # Lets the script run before the API has created the tables.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        try:
            user = await create_user(session, data, data.role)
        except AppError as e:
            raise SystemExit(e.detail)

    # create_user keeps the role of an existing Telegram user, so make sure we really got an admin.
    if user.role != UserRole.ADMIN:
        raise SystemExit("This phone already belongs to a Telegram user; use another number for the admin.")

    await engine.dispose()
    print(f"Admin created: id={user.id}, phone={user.phone}")


if __name__ == "__main__":
    asyncio.run(main())
