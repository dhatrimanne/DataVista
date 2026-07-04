import json

from backend.dashboard.health_score import calculate_business_health_score
from backend.database.connection import db_session


def record_activity(user_id: int, event_type: str, message: str) -> None:
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO activity_events (user_id, event_type, message)
            VALUES (?, ?, ?)
            """,
            (user_id, event_type, message),
        )


def count_user_records(user_id: int, table_name: str) -> int:
    allowed_tables = {"datasets", "reports", "ai_insights", "forecasts"}
    if table_name not in allowed_tables:
        raise ValueError("Unsupported dashboard metric table.")

    with db_session() as connection:
        row = connection.execute(f"SELECT COUNT(*) AS total FROM {table_name} WHERE user_id = ?", (user_id,)).fetchone()
    return int(row["total"])


def list_recent_activity(user_id: int, limit: int = 8) -> list[dict]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id, event_type, message, created_at
            FROM activity_events
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "event_type": row["event_type"],
            "message": row["message"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_latest_analysis(user_id: int) -> dict | None:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT analysis_json
            FROM dataset_analyses
            WHERE user_id = ?
            ORDER BY datetime(updated_at) DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    return json.loads(row["analysis_json"]) if row else None


def get_dashboard_summary(user: dict) -> dict:
    total_datasets = count_user_records(user["id"], "datasets")
    total_reports = count_user_records(user["id"], "reports")
    total_ai_insights = count_user_records(user["id"], "ai_insights")
    total_forecasts = count_user_records(user["id"], "forecasts")
    recent_activity = list_recent_activity(user["id"])

    health = calculate_business_health_score(get_latest_analysis(user["id"]))

    return {
        "total_datasets": total_datasets,
        "total_reports": total_reports,
        "ai_insights_generated": total_ai_insights,
        "forecasts_generated": total_forecasts,
        "recent_activity": recent_activity,
        "last_login_at": user["last_login_at"],
        "business_health_score": health["score"],
        "business_health_status": health["status"],
        "business_health_factors": health["factors"],
    }
