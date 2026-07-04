from fastapi import APIRouter, Depends, Query

from backend.auth.dependencies import get_current_user
from backend.dashboard.repository import list_recent_activity
from backend.dashboard.schemas import ActivityEvent


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[ActivityEvent])
def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> list[dict]:
    return list_recent_activity(current_user["id"], limit=limit)
