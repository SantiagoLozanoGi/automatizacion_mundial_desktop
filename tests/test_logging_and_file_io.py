from __future__ import annotations

import logging
import os
import sys

import pytest

from app.file_io import FileOperationError, open_folder, save_bytes_to_file
from app.logging_config import (
    LOG_BACKUP_COUNT,
    MAX_LOG_BYTES,
    configure_logging,
    get_log_directory,
    install_exception_hook,
    safe_file_metadata,
)


def test_logging_creates_external_directory_and_rotating_handler(tmp_path) -> None:
    logger = logging.getLogger("automatizacion_mundial")
    original_handlers = logger.handlers[:]
    logger.handlers.clear()
    try:
        log_directory = get_log_directory(tmp_path)
        configured = configure_logging(log_directory)
        configured.info("Inicio de prueba documento=1234567890")
        handler = configured.handlers[0]
        handler.flush()

        assert log_directory.is_dir()
        assert (log_directory / "automatizacion_mundial.log").exists()
        assert handler.maxBytes == MAX_LOG_BYTES
        assert handler.backupCount == LOG_BACKUP_COUNT
        assert "1234567890" not in (log_directory / "automatizacion_mundial.log").read_text("utf-8")
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers[:] = original_handlers


def test_safe_file_metadata_omits_filename(tmp_path) -> None:
    source = tmp_path / "Persona Privada 1234567890.xlsx"
    source.write_bytes(b"test")

    metadata = safe_file_metadata(source)

    assert "Persona" not in metadata
    assert metadata == "extension=.xlsx bytes=4"


def test_atomic_file_write_and_invalid_directory(tmp_path) -> None:
    destination = save_bytes_to_file(tmp_path / "salida.pdf", b"%PDF-test")
    assert destination.read_bytes() == b"%PDF-test"
    save_bytes_to_file(destination, b"%PDF-replaced")
    assert destination.read_bytes() == b"%PDF-replaced"
    with pytest.raises(FileNotFoundError):
        save_bytes_to_file(tmp_path / "inexistente" / "salida.pdf", b"data")


def test_file_write_error_is_clear_and_removes_temporary(monkeypatch, tmp_path) -> None:
    def fail_replace(_source, _destination):
        raise PermissionError("locked")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(FileOperationError, match="No fue posible escribir"):
        save_bytes_to_file(tmp_path / "bloqueado.pdf", b"data")
    assert not list(tmp_path.glob("*.tmp"))


def test_open_folder_uses_platform_helper(monkeypatch, tmp_path) -> None:
    opened = []
    monkeypatch.setattr(os, "startfile", lambda path: opened.append(path), raising=False)

    open_folder(tmp_path)

    assert opened == [str(tmp_path)]


def test_global_exception_hook_logs_and_shows_friendly_message(tmp_path) -> None:
    logger = logging.getLogger("automatizacion_mundial")
    original_handlers = logger.handlers[:]
    original_hook = sys.excepthook
    logger.handlers.clear()
    messages = []
    try:
        configure_logging(tmp_path)
        install_exception_hook(messages.append)
        error = RuntimeError("internal failure")
        sys.excepthook(RuntimeError, error, error.__traceback__)
        for handler in logger.handlers:
            handler.flush()

        assert messages == [
            "Ocurrió un error inesperado. La información técnica fue registrada."
        ]
        assert "Excepcion no controlada" in (tmp_path / "automatizacion_mundial.log").read_text("utf-8")
    finally:
        sys.excepthook = original_hook
        for handler in logger.handlers:
            handler.close()
        logger.handlers[:] = original_handlers
