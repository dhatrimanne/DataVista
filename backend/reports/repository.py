from backend.database.connection import db_session


REPORT_COLUMNS = "id, user_id, dataset_id, title, filename, file_size_bytes, created_at"


def create_report(user_id: int, dataset_id: int, title: str, filename: str, file_size_bytes: int) -> dict:
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO reports (user_id, dataset_id, title, filename, file_size_bytes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, dataset_id, title, filename, file_size_bytes),
        )
        row = connection.execute(
            f"SELECT {REPORT_COLUMNS} FROM reports WHERE id = ? AND user_id = ?",
            (cursor.lastrowid, user_id),
        ).fetchone()
    return dict(row)


def list_reports(user_id: int) -> list[dict]:
    with db_session() as connection:
        rows = connection.execute(
            f"SELECT {REPORT_COLUMNS} FROM reports WHERE user_id = ? ORDER BY datetime(created_at) DESC, id DESC",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_report(report_id: int, user_id: int) -> dict | None:
    with db_session() as connection:
        row = connection.execute(
            f"SELECT {REPORT_COLUMNS} FROM reports WHERE id = ? AND user_id = ?",
            (report_id, user_id),
        ).fetchone()
    return dict(row) if row else None


def delete_report(report_id: int, user_id: int) -> bool:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM reports WHERE id = ? AND user_id = ?", (report_id, user_id))
    return cursor.rowcount > 0
