import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_datavista.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-that-is-long-enough")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("CLEANED_DATA_DIR", str(tmp_path / "cleaned"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.chdir(tmp_path)

    from backend.config import get_settings
    import logging
    from backend.utils.logging import LOGGER_NAME
    from backend.app import create_app

    get_settings.cache_clear()
    logging.getLogger(LOGGER_NAME).handlers.clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()
    logging.getLogger(LOGGER_NAME).handlers.clear()
