from __future__ import annotations

import os
from pathlib import Path
import tempfile


class FileOperationError(OSError):
    pass


def save_bytes_to_file(destination: str | Path, content: bytes) -> Path:
    """Write an in-memory output to the location explicitly chosen by the user."""
    path = Path(destination)
    if not isinstance(content, bytes) or not content:
        raise ValueError("El contenido generado está vacío.")
    if not path.parent.is_dir():
        raise FileNotFoundError("La carpeta seleccionada no existe.")
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise FileOperationError(
            "No fue posible escribir el archivo en la ubicación seleccionada."
        ) from error
    return path


def open_folder(path: str | Path) -> None:
    folder = Path(path)
    if not folder.is_dir():
        raise FileNotFoundError("La carpeta seleccionada no existe.")
    startfile = getattr(os, "startfile", None)
    if startfile is None:
        raise FileOperationError("La apertura de carpetas no está disponible en este sistema.")
    try:
        startfile(str(folder))
    except OSError as error:
        raise FileOperationError("No fue posible abrir la carpeta seleccionada.") from error
