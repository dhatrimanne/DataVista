import json

from backend.database.connection import db_session


def save_analysis(dataset_id: int, user_id: int, analysis: dict) -> None:
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO dataset_analyses (dataset_id, user_id, analysis_json)
            VALUES (?, ?, ?)
            ON CONFLICT(dataset_id, user_id) DO UPDATE SET
                analysis_json = excluded.analysis_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (dataset_id, user_id, json.dumps(analysis)),
        )


def get_analysis(dataset_id: int, user_id: int) -> dict | None:
    with db_session() as connection:
        row = connection.execute(
            """
            SELECT analysis_json, created_at, updated_at
            FROM dataset_analyses
            WHERE dataset_id = ? AND user_id = ?
            """,
            (dataset_id, user_id),
        ).fetchone()
    if row is None:
        return None
    return {
        **json.loads(row["analysis_json"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
