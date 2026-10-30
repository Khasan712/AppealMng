from fastapi import APIRouter, Depends, status

from app.deps import SessionDep, role_checker
from app.models import UserRole
from app.schemas import UserCreate, UserRead
from app.services import users as user_service


router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(role_checker(UserRole.ADMIN))],
)


@router.get("", response_model=list[UserRead])
async def get_users_list(session: SessionDep, role: UserRole | None = None):
    return await user_service.get_users_list(session, role)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, session: SessionDep):
    return await user_service.create_user(session, data, data.role)
