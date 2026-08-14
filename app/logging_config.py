from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
from typing import Callable


LOGGER_NAME = "automatizacion_mundial"
MAX_LOG_BYTES = 3 * 1024 * 1024
LOG_BACKUP_COUNT = 5


class PrivacyFormatter(logging.Formatter):
    """Redact common paths and long numeric identifiers from log messages."""

    _windows_path = re.compile(r"[A-Za-z]:\\[^\r\n'\"]+")
    _long_number = re.compile(r"\b\d{6,}\b")

    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        rendered = self._windows_path.sub("<ruta omitida>", rendered)
        return self._long_number.sub("<numero omitido>", rendered)


def get_log_directory(base_directory: str | Path | None = None) -> Path:
    if base_directory is not None:
        root = Path(base_directory)
    else:
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return root / "AutomatizacionMundial" / "logs"


def configure_logging(log_directory: str | Path | None = None) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if any(getattr(handler, "_automatizacion_handler", False) for handler in logger.handlers):
        return logger

    directory = Path(log_directory) if log_directory else get_log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        directory / "automatizacion_mundial.log",
        maxBytes=MAX_LOG_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler._automatizacion_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(
        PrivacyFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
    return logger


def get_logger(component: str | None = None) -> logging.Logger:
    base = logging.getLogger(LOGGER_NAME)
    return base.getChild(component) if component else base


def safe_file_metadata(path: str | Path) -> str:
    file_path = Path(path)
    try:
        size = file_path.stat().st_size
    except OSError:
        size = -1
    return f"extension={file_path.suffix.lower() or '<sin extension>'} bytes={size}"


def install_exception_hook(show_friendly_error: Callable[[str], None]) -> None:
    logger = get_logger("unhandled")
    previous_hook = sys.excepthook

    def handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Excepcion no controlada tipo=%s",
            exc_type.__name__,
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        show_friendly_error(
            "Ocurrió un error inesperado. La información técnica fue registrada."
        )

    sys.excepthook = handle_exception
