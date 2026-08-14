from __future__ import annotations

from PySide6 import QtWidgets

from workflows.certificados_icbf.view import CertificadosIcbfView


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Automatización Mundial")
        self.resize(1024, 720)
        self.central = CertificadosIcbfView()
        self.setCentralWidget(self.central)


def run_app() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
