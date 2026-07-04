from datetime import UTC, datetime
from sqlite3 import IntegrityError, Row

from backend.database.connection import db_session


def row_to_user(row: Row | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "hashed_password": row["hashed_password"],
        "theme": row["theme"],
        "preferred_gemini_model": row["preferred_gemini_model"],
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
        "is_active": bool(row["is_active"]),
    }


def create_user(email: str, full_name: str, hashed_password: str) -> dict:
    try:
        with db_session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (email, full_name, hashed_password)
                VALUES (?, ?, ?)
                """,
                (email.lower(), full_name.strip(), hashed_password),
            )
            user_id = cursor.lastrowid
            row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except IntegrityError as exc:
        raise ValueError("A user with this email already exists.") from exc
    user = row_to_user(row)
    if user is None:
        raise RuntimeError("User creation failed.")
    return user


def get_user_by_email(email: str) -> dict | None:
    with db_session() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return row_to_user(row)


def get_user_by_id(user_id: int) -> dict | None:
    with db_session() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row)


def update_last_login(user_id: int) -> None:
    timestamp = datetime.now(UTC).isoformat()
    with db_session() as connection:
        connection.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (timestamp, user_id))


def revoke_token(token: str) -> None:
    with db_session() as connection:
        connection.execute("INSERT OR IGNORE INTO revoked_tokens (token) VALUES (?)", (token,))


def is_token_revoked(token: str) -> bool:
    with db_session() as connection:
        row = connection.execute("SELECT token FROM revoked_tokens WHERE token = ?", (token,)).fetchone()
    return row is not None


def update_profile(user_id: int, full_name: str) -> dict | None:
    with db_session() as connection:
        connection.execute("UPDATE users SET full_name = ? WHERE id = ? AND is_active = 1", (full_name.strip(), user_id))
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row)


def update_password(user_id: int, hashed_password: str) -> None:
    with db_session() as connection:
        connection.execute("UPDATE users SET hashed_password = ? WHERE id = ?", (hashed_password, user_id))


def update_preferences(user_id: int, theme: str, preferred_gemini_model: str | None) -> dict | None:
    with db_session() as connection:
        connection.execute(
            "UPDATE users SET theme = ?, preferred_gemini_model = ? WHERE id = ? AND is_active = 1",
            (theme, preferred_gemini_model, user_id),
        )
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return row_to_user(row)


def deactivate_user(user_id: int) -> None:
    with db_session() as connection:
        connection.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
