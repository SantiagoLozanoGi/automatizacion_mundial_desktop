from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app.main_window import MainWindow
from workflows.certificados_icbf.view import CertificadosIcbfView


def application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_main_window_and_certificates_view_construct() -> None:
    app = application()
    window = MainWindow()

    assert window.pages.count() == 2
    assert isinstance(window.certificates, CertificadosIcbfView)
    assert window.certificates.workspace.count() == 2
    assert window.certificates.table.sizePolicy().verticalPolicy() == QtWidgets.QSizePolicy.Expanding
    assert app is QtWidgets.QApplication.instance()

    window.close()
