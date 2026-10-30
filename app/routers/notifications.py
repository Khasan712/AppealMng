from fastapi import APIRouter
from app.deps import CurrentUser, SessionDep
from app.schemas import NotificationRead
from app.services import notifications as notification_service


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def get_my_notifications(session: SessionDep, user: CurrentUser):
    return await notification_service.get_notifications_list(session, user)
