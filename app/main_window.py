from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from config.resources import CORPORATE_LOGO_PATH
from version import APP_VERSION
from workflows.certificados_icbf.view import CertificadosIcbfView


class HomeView(QtWidgets.QWidget):
    open_certificates = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(48, 36, 48, 36)
        layout.setSpacing(18)

        logo = QtWidgets.QLabel()
        logo.setAlignment(QtCore.Qt.AlignCenter)
        if CORPORATE_LOGO_PATH.exists():
            logo.setPixmap(QtGui.QPixmap(str(CORPORATE_LOGO_PATH)).scaled(
                260, 120, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            ))
        layout.addWidget(logo)

        title = QtWidgets.QLabel("Automatización de Procesos – Mundial de Seguros")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        version = QtWidgets.QLabel(f"Versión {APP_VERSION}")
        version.setAlignment(QtCore.Qt.AlignCenter)
        version.setStyleSheet("color: #64748b;")
        layout.addWidget(version)
        layout.addSpacing(24)

        certificates = QtWidgets.QPushButton("Abrir Certificados ICBF")
        certificates.setMinimumHeight(46)
        certificates.clicked.connect(self.open_certificates.emit)
        layout.addWidget(certificates)
        layout.addStretch()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Automatización de Procesos – Mundial de Seguros {APP_VERSION}")
        self.resize(1180, 760)

        root = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navigation = QtWidgets.QListWidget()
        self.navigation.setFixedWidth(220)
        self.navigation.addItems(["Inicio", "Certificados ICBF"])
        self.navigation.setCurrentRow(0)
        self.navigation.currentRowChanged.connect(self._show_page)
        layout.addWidget(self.navigation)

        self.pages = QtWidgets.QStackedWidget()
        self.home = HomeView()
        self.certificates = CertificadosIcbfView()
        self.home.open_certificates.connect(lambda: self.navigation.setCurrentRow(1))
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.certificates)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

    @QtCore.Slot(int)
    def _show_page(self, index: int) -> None:
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)


def run_app() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
