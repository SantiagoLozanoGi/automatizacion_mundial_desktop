from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app.main_window import MainWindow
from app.workflow_contract import WorkflowDefinition
from app.workflow_registry import WorkflowRegistry, workflow_registry
from workflows.certificados_icbf.view import CertificadosIcbfView


class StubView(QtWidgets.QWidget):
    pass


def definition(workflow_id: str = "test", *, enabled: bool = True) -> WorkflowDefinition:
    return WorkflowDefinition(
        id=workflow_id,
        name="Flujo de prueba",
        description="Definición exclusiva de las pruebas.",
        view_class=StubView,
        enabled=enabled,
    )


def application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_certificados_icbf_is_the_only_registered_workflow() -> None:
    registered = workflow_registry.all()

    assert len(registered) == 1
    assert registered[0].id == "certificados_icbf"
    assert registered[0].name == "Certificados ICBF"
    assert registered[0].description
    assert registered[0].view_class is CertificadosIcbfView
    assert registered[0].enabled is True


def test_registry_rejects_duplicate_ids() -> None:
    registry = WorkflowRegistry([definition()])

    with pytest.raises(ValueError, match="duplicado"):
        registry.register(definition())


@pytest.mark.parametrize("field", ["id", "name", "description"])
def test_required_metadata_is_validated(field: str) -> None:
    values = {
        "id": "test",
        "name": "Flujo de prueba",
        "description": "Descripción",
        "view_class": StubView,
    }
    values[field] = " "

    with pytest.raises(ValueError):
        WorkflowDefinition(**values)


def test_view_class_must_be_a_widget_class() -> None:
    with pytest.raises(TypeError, match="QWidget"):
        WorkflowDefinition("test", "Test", "Descripción", object)


def test_disabled_workflow_is_not_exposed() -> None:
    registry = WorkflowRegistry([definition("enabled"), definition("disabled", enabled=False)])

    assert [item.id for item in registry.enabled()] == ["enabled"]


def test_workflow_load_failure_returns_home_and_keeps_window_open(monkeypatch) -> None:
    application()

    class BrokenView(QtWidgets.QWidget):
        def __init__(self) -> None:
            raise RuntimeError("fallo esperado")

    broken = WorkflowDefinition("broken", "Roto", "Prueba de error", BrokenView)
    window = MainWindow(WorkflowRegistry([broken]))
    messages = []
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: messages.append(args))

    window.open_workflow("broken")

    assert window.navigation.currentRow() == 0
    assert window.pages.currentWidget() is window.home
    assert "broken" not in window.workflow_views
    assert messages
    window.close()
