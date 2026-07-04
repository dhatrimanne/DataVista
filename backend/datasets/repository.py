import json
from sqlite3 import IntegrityError

from backend.database.connection import db_session


DATASET_COLUMNS = """
    id, user_id, name, original_filename, stored_filename, cleaned_filename,
    content_hash, file_type, file_size_bytes, row_count, column_count, missing_value_count,
    data_quality_score, cleaning_report, status, created_at, updated_at
"""


def dataset_row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "original_filename": row["original_filename"],
        "stored_filename": row["stored_filename"],
        "cleaned_filename": row["cleaned_filename"],
        "content_hash": row["content_hash"],
        "file_type": row["file_type"],
        "file_size_bytes": row["file_size_bytes"],
        "row_count": row["row_count"],
        "column_count": row["column_count"],
        "missing_value_count": row["missing_value_count"],
        "data_quality_score": row["data_quality_score"],
        "cleaning_report": json.loads(row["cleaning_report"]) if row["cleaning_report"] else None,
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def public_dataset(dataset: dict) -> dict:
    return {
        "id": dataset["id"],
        "name": dataset["name"],
        "original_filename": dataset["original_filename"],
        "file_type": dataset["file_type"],
        "file_size_bytes": dataset["file_size_bytes"],
        "row_count": dataset["row_count"],
        "column_count": dataset["column_count"],
        "missing_value_count": dataset["missing_value_count"],
        "data_quality_score": dataset["data_quality_score"],
        "status": dataset["status"],
        "created_at": dataset["created_at"],
        "updated_at": dataset["updated_at"],
    }


def create_dataset(user_id: int, metadata: dict) -> dict:
    try:
        with db_session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO datasets (
                    user_id, name, original_filename, stored_filename, cleaned_filename,
                    content_hash, file_type, file_size_bytes, row_count, column_count, missing_value_count,
                    data_quality_score, cleaning_report, status, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    user_id,
                    metadata["name"],
                    metadata["original_filename"],
                    metadata["stored_filename"],
                    metadata["cleaned_filename"],
                    metadata["content_hash"],
                    metadata["file_type"],
                    metadata["file_size_bytes"],
                    metadata["row_count"],
                    metadata["column_count"],
                    metadata["missing_value_count"],
                    metadata.get("data_quality_score"),
                    json.dumps(metadata.get("cleaning_report")),
                    metadata["status"],
                ),
            )
            dataset_id = cursor.lastrowid
            add_history_event(dataset_id, user_id, "uploaded", "Dataset uploaded.", connection=connection)
            row = connection.execute(f"SELECT {DATASET_COLUMNS} FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    except IntegrityError as exc:
        raise ValueError("This dataset has already been uploaded to your workspace.") from exc
    dataset = dataset_row_to_dict(row)
    if dataset is None:
        raise RuntimeError("Dataset creation failed.")
    return dataset


def list_datasets(user_id: int) -> list[dict]:
    with db_session() as connection:
        rows = connection.execute(
            f"""
            SELECT {DATASET_COLUMNS}
            FROM datasets
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (user_id,),
        ).fetchall()
    return [dataset_row_to_dict(row) for row in rows]


def get_dataset_by_hash(user_id: int, content_hash: str) -> dict | None:
    with db_session() as connection:
        row = connection.execute(
            f"SELECT {DATASET_COLUMNS} FROM datasets WHERE user_id = ? AND content_hash = ?",
            (user_id, content_hash),
        ).fetchone()
    return dataset_row_to_dict(row)


def get_dataset(dataset_id: int, user_id: int) -> dict | None:
    with db_session() as connection:
        row = connection.execute(
            f"SELECT {DATASET_COLUMNS} FROM datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()
    return dataset_row_to_dict(row)


def rename_dataset(dataset_id: int, user_id: int, name: str) -> dict | None:
    clean_name = name.strip()
    with db_session() as connection:
        connection.execute(
            """
            UPDATE datasets
            SET name = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (clean_name, dataset_id, user_id),
        )
        add_history_event(dataset_id, user_id, "renamed", f"Dataset renamed to {clean_name}.", connection=connection)
        row = connection.execute(
            f"SELECT {DATASET_COLUMNS} FROM datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()
    return dataset_row_to_dict(row)


def mark_reanalyzed(dataset_id: int, user_id: int, metadata: dict) -> dict | None:
    with db_session() as connection:
        connection.execute(
            """
            UPDATE datasets
            SET row_count = ?, column_count = ?, missing_value_count = ?,
                data_quality_score = ?, cleaning_report = ?,
                status = 'analyzed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
            """,
            (
                metadata["row_count"],
                metadata["column_count"],
                metadata["missing_value_count"],
                metadata.get("data_quality_score"),
                json.dumps(metadata.get("cleaning_report")),
                dataset_id,
                user_id,
            ),
        )
        add_history_event(dataset_id, user_id, "reanalyzed", "Dataset re-analyzed.", connection=connection)
        row = connection.execute(
            f"SELECT {DATASET_COLUMNS} FROM datasets WHERE id = ? AND user_id = ?",
            (dataset_id, user_id),
        ).fetchone()
    return dataset_row_to_dict(row)


def delete_dataset(dataset_id: int, user_id: int) -> bool:
    with db_session() as connection:
        cursor = connection.execute("DELETE FROM datasets WHERE id = ? AND user_id = ?", (dataset_id, user_id))
    return cursor.rowcount > 0


def add_history_event(dataset_id: int, user_id: int, event_type: str, message: str, connection=None) -> None:
    owns_connection = connection is None
    if owns_connection:
        context = db_session()
        connection = context.__enter__()
    try:
        connection.execute(
            """
            INSERT INTO dataset_history (dataset_id, user_id, event_type, message)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_id, user_id, event_type, message),
        )
    finally:
        if owns_connection:
            context.__exit__(None, None, None)


def list_dataset_history(dataset_id: int, user_id: int) -> list[dict]:
    with db_session() as connection:
        rows = connection.execute(
            """
            SELECT id, event_type, message, created_at
            FROM dataset_history
            WHERE dataset_id = ? AND user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (dataset_id, user_id),
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
