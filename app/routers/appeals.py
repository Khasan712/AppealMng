from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from app.deps import CurrentUser, SessionDep, role_checker
from app.models import AppealStatus, UserRole
from app.schemas import AppealCreate, AppealDetail, AppealRead, CategoryChangeIn, OptionalCommentIn, RequiredCommentIn
from app.services import appeals as appeal_service


router = APIRouter(prefix="/api/appeals", tags=["appeals"])
staff_only = [Depends(role_checker(UserRole.MANAGER, UserRole.ADMIN))]


@router.post("", response_model=AppealRead, status_code=status.HTTP_201_CREATED)
async def create_appeal(data: AppealCreate, session: SessionDep, user: CurrentUser):
    return await appeal_service.create_appeal(session, data, user)


@router.get("", response_model=list[AppealRead])
async def get_appeals_list(
    session: SessionDep,
    user: CurrentUser,
    appeal_status: Annotated[AppealStatus | None, Query(alias="status")] = None,  # ?status=NEW
    category_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    return await appeal_service.get_appeals_list(session, user, appeal_status, category_id, limit, offset)


@router.get("/{appeal_id}", response_model=AppealDetail)
async def get_appeal(appeal_id: int, session: SessionDep, user: CurrentUser):
    return await appeal_service.get_appeal(session, appeal_id, user)


@router.post("/{appeal_id}/accept", response_model=AppealDetail, dependencies=staff_only)
async def accept_appeal(appeal_id: int, data: OptionalCommentIn, session: SessionDep, user: CurrentUser):
    return await appeal_service.change_status(session, appeal_id, user, AppealStatus.IN_PROGRESS, data.comment)


@router.post("/{appeal_id}/reject", response_model=AppealDetail, dependencies=staff_only)
async def reject_appeal(appeal_id: int, data: RequiredCommentIn, session: SessionDep, user: CurrentUser):
    return await appeal_service.change_status(session, appeal_id, user, AppealStatus.REJECTED, data.comment)


@router.post("/{appeal_id}/close", response_model=AppealDetail, dependencies=staff_only)
async def close_appeal(appeal_id: int, data: RequiredCommentIn, session: SessionDep, user: CurrentUser):
    return await appeal_service.change_status(session, appeal_id, user, AppealStatus.CLOSED, data.comment)


@router.patch("/{appeal_id}/category", response_model=AppealDetail, dependencies=staff_only)
async def change_appeal_category(appeal_id: int, data: CategoryChangeIn, session: SessionDep, user: CurrentUser):
    return await appeal_service.change_category(session, appeal_id, user, data.category_id, data.comment)
