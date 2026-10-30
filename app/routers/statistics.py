from fastapi import APIRouter, Depends
from app.deps import SessionDep, role_checker
from app.models import UserRole
from app.schemas import StatsRead
from app.services import statistics


router = APIRouter(
    prefix="/api/stats",
    tags=["stats"],
    dependencies=[Depends(role_checker(UserRole.ADMIN))],
)


@router.get("", response_model=StatsRead)
async def get_stats(session: SessionDep):
    return await statistics.get_stats_list(session)
