from fastapi import APIRouter, Depends, status
from app.deps import CurrentUser, SessionDep, role_checker
from app.models import UserRole
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate
from app.services import categories as category_service


router = APIRouter(prefix="/api/categories", tags=["categories"])

admin_only = [Depends(role_checker(UserRole.ADMIN))]


@router.get("", response_model=list[CategoryRead])
async def get_categories_list(session: SessionDep, _: CurrentUser):  # appealers need categories too
    return await category_service.get_categories(session)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
async def create_category(data: CategoryCreate, session: SessionDep):
    return await category_service.create_category(session, data)


@router.patch("/{category_id}", response_model=CategoryRead, dependencies=admin_only)
async def update_category(category_id: int, data: CategoryUpdate, session: SessionDep):
    return await category_service.update_category(session, category_id, data)
