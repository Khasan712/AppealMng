from typing import Annotated
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.deps import CurrentUser, SessionDep
from app.schemas import Token, UserRead, UserRegister
from app.security import create_access_token
from app.services import users as user_service


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, session: SessionDep):
    return await user_service.create_user(session, data)


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep):
    user = await user_service.authenticate(session, form.username, form.password)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser):
    return user

