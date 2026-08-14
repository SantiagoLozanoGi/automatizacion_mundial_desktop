from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from app.main_window import MainWindow
from workflows.certificados_icbf.view import CertificadosIcbfView, ExcelProcessorWorker


def application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_main_window_and_certificates_view_construct() -> None:
    app = application()
    window = MainWindow()

    assert window.pages.count() == 1
    window.open_workflow("certificados_icbf")
    certificates = window.workflow_views["certificados_icbf"]
    assert window.pages.count() == 2
    assert isinstance(certificates, CertificadosIcbfView)
    assert certificates.workspace.count() == 2
    assert certificates.table.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding
    assert app is QtWidgets.QApplication.instance()

    window.close()


def processed_records() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "INCLUIR": True,
            "PRIMER NOMBRE": "Ana",
            "SEGUNDO NOMBRE": "NA",
            "PRIMER APELLIDO": "Díaz",
            "SEGUNDO APELLIDO": "NA",
            "DOCUMENTO": "0000000123",
            "FECHA DE NACIMIENTO": "01/01/2010",
            "UNIDADES": "Bogotá",
            "_FILA_ORIGEN": 2,
        }
    ])


def test_cancelled_save_is_not_an_error(monkeypatch, tmp_path) -> None:
    app = application()
    view = CertificadosIcbfView()
    view.file_path = tmp_path / "entrada.xlsx"
    critical_messages = []
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", lambda *args: ("", ""))
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "critical", lambda *args: critical_messages.append(args)
    )

    view._request_save(b"%PDF-test", "pdf")

    assert "cancelado" in view.generation_status.text().lower()
    assert critical_messages == []
    assert app is QtWidgets.QApplication.instance()
    view.close()


def test_save_remembers_directory_and_preserves_review_state(monkeypatch, tmp_path) -> None:
    application()
    view = CertificadosIcbfView()
    view.file_path = tmp_path / "entrada.xlsx"
    records = processed_records()
    view._show_results(records, {"recibidos": 1, "ingresos": 1, "excluidos": 0}, "correo")
    original = view.table_model.records
    destination = tmp_path / "salida.pdf"
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getSaveFileName", lambda *args: (str(destination), "")
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox, "question", lambda *args: QtWidgets.QMessageBox.No
    )

    view._request_save(b"%PDF-test", "pdf")

    assert destination.read_bytes() == b"%PDF-test"
    assert view._last_save_directory == tmp_path
    assert view.table_model.records.equals(original)
    view.close()


def test_generation_error_keeps_processed_state(monkeypatch) -> None:
    application()
    view = CertificadosIcbfView()
    records = processed_records()
    view._show_results(records, {"recibidos": 1, "ingresos": 1, "excluidos": 0}, "correo")
    original = view.table_model.records
    monkeypatch.setattr(QtWidgets.QMessageBox, "critical", lambda *args: None)

    view._generation_failed("pdf", "No fue posible generar la salida.")

    assert view.table_model.records.equals(original)
    assert "conservaron" in view.generation_status.text()
    view.close()


def test_manual_table_edit_refreshes_workflow_status_and_summary() -> None:
    application()
    view = CertificadosIcbfView()
    records = processed_records()
    records.loc[0, "DOCUMENTO"] = "NA"
    view._show_results(records, {"recibidos": 1, "ingresos": 1, "excluidos": 0}, "correo")
    document_column = view.table_model._columns.index("DOCUMENTO")

    assert view.table_model.setData(
        view.table_model.index(0, document_column), "1234567890", QtCore.Qt.EditRole
    )

    assert view.table_model.records.loc[0, "DOCUMENTO"] == "1234567890"
    assert "Listo para generaci" in view.workflow_status.text()
    assert view.metrics["invalidos"].text() == "0"
    assert view.pdf_button.isEnabled()
    view.close()


def test_main_window_refuses_close_while_busy(monkeypatch) -> None:
    application()
    window = MainWindow()
    window.open_workflow("certificados_icbf")
    certificates = window.workflow_views["certificados_icbf"]
    certificates._synchronous_busy = True
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", lambda *args: None)
    event = QtGui.QCloseEvent()

    window.closeEvent(event)

    assert not event.isAccepted()
    certificates._synchronous_busy = False
    window.close()


def test_navigation_reuses_workflow_view_and_preserves_state() -> None:
    application()
    window = MainWindow()
    window.open_workflow("certificados_icbf")
    certificates = window.workflow_views["certificados_icbf"]
    records = processed_records()
    certificates._show_results(
        records, {"recibidos": 1, "ingresos": 1, "excluidos": 0}, "correo"
    )

    window.navigation.setCurrentRow(0)
    window.open_workflow("certificados_icbf")

    assert window.workflow_views["certificados_icbf"] is certificates
    assert certificates.table_model.records.equals(records)
    window.close()


def test_invalid_excel_worker_returns_friendly_error(tmp_path) -> None:
    invalid = tmp_path / "invalido.xlsx"
    invalid.write_bytes(b"not-an-excel")
    messages = []
    worker = ExcelProcessorWorker(invalid)
    worker.failed.connect(messages.append)

    worker.run()

    assert len(messages) == 1
    assert "Excel válido" in messages[0]
    assert "Traceback" not in messages[0]


def test_file_selection_remembers_last_open_directory(monkeypatch, tmp_path) -> None:
    application()
    source = tmp_path / "entrada.xlsx"
    source.write_bytes(b"placeholder")
    view = CertificadosIcbfView()
    monkeypatch.setattr(
        QtWidgets.QFileDialog, "getOpenFileName", lambda *args: (str(source), "")
    )

    view._select_file()

    assert view.file_path == source
    assert view._last_open_directory == tmp_path
    assert view.process_button.isEnabled()
    view.close()


def test_review_table_shows_at_least_eight_rows_at_enterprise_resolution() -> None:
    app = application()
    view = CertificadosIcbfView()
    view.resize(1180, 700)
    base = processed_records().iloc[0].to_dict()
    records = pd.DataFrame([
        {**base, "DOCUMENTO": str(index).zfill(10), "_FILA_ORIGEN": index + 2}
        for index in range(20)
    ])
    view._show_results(
        records, {"recibidos": 20, "ingresos": 20, "excluidos": 0}, "correo"
    )
    view.show()
    app.processEvents()

    visible_rows = view.table.viewport().height() // view.table.rowHeight(0)
    assert view.minimumSizeHint().width() <= 1366
    assert view.minimumSizeHint().height() <= 768
    assert visible_rows >= 8
    view.close()


def test_main_window_restored_geometry_respects_available_desktop(monkeypatch) -> None:
    app = application()

    class EnterpriseScreen:
        def availableGeometry(self):
            return QtCore.QRect(0, 0, 1366, 728)

    monkeypatch.setattr(MainWindow, "screen", lambda self: EnterpriseScreen())
    window = MainWindow()
    window.open_workflow("certificados_icbf")
    certificates = window.workflow_views["certificados_icbf"]
    base = processed_records().iloc[0].to_dict()
    records = pd.DataFrame([
        {**base, "DOCUMENTO": str(index).zfill(10), "_FILA_ORIGEN": index + 2}
        for index in range(20)
    ])
    certificates._show_results(
        records, {"recibidos": 20, "ingresos": 20, "excluidos": 0}, ""
    )
    window.show()
    app.processEvents()
    geometry = window.geometry()

    assert geometry.left() >= 0
    assert geometry.top() >= 0
    assert geometry.right() < 1366
    assert geometry.bottom() < 728
    assert certificates.table.viewport().height() // certificates.table.rowHeight(0) >= 5
    assert app is QtWidgets.QApplication.instance()
    window.close()


def test_document_authorization_action_has_clear_pending_and_authorized_states() -> None:
    app = application()
    view = CertificadosIcbfView()
    records = processed_records()
    records.loc[0, "DOCUMENTO"] = "PAS12345"
    view._show_results(records, {"recibidos": 1, "ingresos": 1, "excluidos": 0}, "")
    view.show()
    view.table.selectRow(0)
    app.processEvents()

    assert view.document_exception_button.isVisible()
    assert view.document_exception_button.text() == "Autorizar documento no estándar"
    assert view.document_exception_button.property("authorizationState") == "pending"
    assert "requiere autorización" in view.detail.text()

    view.table_model.authorize_document_exception(0)
    app.processEvents()

    assert view.document_exception_button.text() == "Revocar autorización"
    assert view.document_exception_button.property("authorizationState") == "authorized"
    assert "✓ Documento no estándar autorizado" in view.detail.text()
    view.close()
