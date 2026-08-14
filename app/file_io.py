from __future__ import annotations

from pathlib import Path


def save_bytes_to_file(destination: str | Path, content: bytes) -> Path:
    """Write an in-memory output to the location explicitly chosen by the user."""
    path = Path(destination)
    if not isinstance(content, bytes) or not content:
        raise ValueError("El contenido generado está vacío.")
    if not path.parent.is_dir():
        raise FileNotFoundError("La carpeta seleccionada no existe.")
    path.write_bytes(content)
    return path
