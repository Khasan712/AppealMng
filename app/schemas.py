import re
from datetime import datetime
from typing import Annotated
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints
from app.models import UserRole, AppealStatus, AppealSource


def normalize_phone(v: str) -> str:
    cleaned = re.sub(r"[\s\-()]", "", v)
    if not re.fullmatch(r"\+998\d{9}", cleaned):
        raise ValueError("Phone must be in +998XXXXXXXXX format")
    return cleaned


Phone = Annotated[str, AfterValidator(normalize_phone)]
Password = Annotated[str, Field(min_length=8, max_length=72)]  # bcrypt accepts at most 72 bytes
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
CategoryName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2000)]


# No role field: self-registration always creates an APPEALER.
class UserRegister(BaseModel):
    phone: Phone
    password: Password
    full_name: FullName | None = None


class UserCreate(UserRegister):
    role: UserRole = UserRole.MANAGER


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    full_name: str | None
    role: UserRole
    telegram_id: int | None
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCommonData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    full_name: str | None


class CategoryCreate(BaseModel):
    name: CategoryName
    responsible_user_id: int


class CategoryUpdate(BaseModel):
    name: CategoryName | None = None
    responsible_user_id: int | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    responsible_user_id: int
    responsible_user: UserCommonData


# author, status and source are set by the server, never taken from the client.
class AppealCreate(BaseModel):
    phone: Phone
    description: Description
    category_id: int


class AppealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    description: str
    status: AppealStatus
    source: AppealSource
    category_id: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    category: CategoryRead
    author: UserCommonData


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    previous_status: AppealStatus | None
    new_status: AppealStatus
    comment: str | None
    created_at: datetime
    updated_by: UserCommonData


class AppealDetail(AppealRead):
    history: list[StatusHistoryRead]


class OptionalCommentIn(BaseModel):
    comment: Comment | None = None


class RequiredCommentIn(BaseModel):
    comment: Comment


class CategoryChangeIn(BaseModel):
    category_id: int
    comment: Comment | None = None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    appeal_id: int
    message: str
    is_read: bool
    created_at: datetime


class CategoryCount(BaseModel):
    category_id: int
    name: str
    count: int


class StatsRead(BaseModel):
    total: int
    by_status: dict[AppealStatus, int]
    by_category: list[CategoryCount]
    accepted: int
    rejected: int
    closed: int
