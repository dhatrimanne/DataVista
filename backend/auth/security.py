from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

import bcrypt
from jose import JWTError, jwt

from backend.config import get_settings


ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    password_bytes = sha256(password.encode("utf-8")).digest()
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = sha256(plain_password.encode("utf-8")).digest()
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_access_token(subject: str, remember_me: bool = False) -> str:
    settings = get_settings()
    minutes = settings.access_token_expire_minutes
    if remember_me:
        minutes *= 4
    expire = datetime.now(UTC) + timedelta(minutes=minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": int(expire.timestamp())}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    except JWTError:
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None
