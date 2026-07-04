from backend.database.connection import db_session


def record_ai_insight(user_id: int, dataset_id: int) -> None:
    with db_session() as connection:
        connection.execute(
            "INSERT INTO ai_insights (user_id, dataset_id) VALUES (?, ?)",
            (user_id, dataset_id),
        )
