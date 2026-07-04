from backend.database.connection import db_session


def record_forecast(user_id: int, dataset_id: int, model_name: str) -> None:
    with db_session() as connection:
        connection.execute(
            "INSERT INTO forecasts (user_id, dataset_id, model_name) VALUES (?, ?, ?)",
            (user_id, dataset_id, model_name),
        )
