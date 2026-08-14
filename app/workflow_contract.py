from __future__ import annotations

from dataclasses import dataclass

from PySide6 import QtWidgets


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Metadata and UI integration contract for an application workflow."""

    id: str
    name: str
    description: str
    view_class: type[QtWidgets.QWidget]
    icon: str | None = None
    version: str | None = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("El ID del workflow es obligatorio.")
        if not self.name.strip():
            raise ValueError("El nombre del workflow es obligatorio.")
        if not self.description.strip():
            raise ValueError("La descripción del workflow es obligatoria.")
        if not isinstance(self.view_class, type) or not issubclass(
            self.view_class, QtWidgets.QWidget
        ):
            raise TypeError("view_class debe ser una subclase de QWidget.")

    def create_view(self) -> QtWidgets.QWidget:
        return self.view_class()
