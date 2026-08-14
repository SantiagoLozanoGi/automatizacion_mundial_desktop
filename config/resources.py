from __future__ import annotations

from pathlib import Path
import sys


def resource_path(relative_path: str | Path) -> Path:
    """Resolve project assets both from source and from a packaged application."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    base_path = Path(bundle_root) if bundle_root else Path(__file__).resolve().parents[1]
    return base_path / relative_path


CORPORATE_LOGO_PATH = resource_path("assets/Logo_mundial_seguros.png")
