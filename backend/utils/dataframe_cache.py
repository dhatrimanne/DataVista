from __future__ import annotations

from functools import lru_cache
from hashlib import blake2b
from pathlib import Path

import pandas as pd


def file_digest(path: Path) -> str:
    digest = blake2b(digest_size=12)
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=64)
def _read_csv_cached(path: str, modified_ns: int, size: int, digest: str) -> pd.DataFrame:
    return pd.read_csv(path)


def read_csv_cached(path: Path) -> pd.DataFrame:
    stat = path.stat()
    return _read_csv_cached(str(path), stat.st_mtime_ns, stat.st_size, file_digest(path)).copy()


def clear_dataframe_cache() -> None:
    _read_csv_cached.cache_clear()
