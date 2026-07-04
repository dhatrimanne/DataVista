from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from backend.config import get_settings, resolve_app_path


LOGGER_NAME = "datavista"


def configure_logging() -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return

    log_path = resolve_app_path(get_settings().log_dir) / "datavista.log"
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)


def get_logger() -> logging.Logger:
    configure_logging()
    return logging.getLogger(LOGGER_NAME)
