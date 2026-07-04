import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from backend.config import get_settings, resolve_sqlite_path


def get_connection() -> sqlite3.Connection:
    db_path = resolve_sqlite_path(get_settings().database_url)
    connection = sqlite3.connect(db_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
