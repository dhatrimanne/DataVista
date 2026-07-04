from pydantic import BaseModel


class ActivityEvent(BaseModel):
    id: int
    event_type: str
    message: str
    created_at: str


class DashboardSummary(BaseModel):
    total_datasets: int
    total_reports: int
    ai_insights_generated: int
    forecasts_generated: int
    recent_activity: list[ActivityEvent]
    last_login_at: str | None
    business_health_score: int | None
    business_health_status: str
    business_health_factors: list[dict]
