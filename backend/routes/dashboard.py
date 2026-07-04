from fastapi import APIRouter, Depends

from backend.auth.dependencies import get_current_user
from backend.dashboard.repository import get_dashboard_summary
from backend.dashboard.schemas import DashboardSummary


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(current_user: dict = Depends(get_current_user)) -> dict:
    return get_dashboard_summary(current_user)
