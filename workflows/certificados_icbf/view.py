from __future__ import annotations

from PySide6 import QtWidgets

from workflows.certificados_icbf.service import service


class CertificadosIcbfView(QtWidgets.QWidget):
    """Vista base para la migración. No implementa reglas de negocio."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Certificados ICBF")
        self.resize(900, 600)

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Migración controlada de lógica heredada")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        self.status = QtWidgets.QLabel("Servicio listo para procesar archivos.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.button = QtWidgets.QPushButton("Validar servicio")
        self.button.clicked.connect(self._on_validate)
        layout.addWidget(self.button)

    def _on_validate(self) -> None:
        self.status.setText(
            "Servicio activo: "
            + str(service.__class__.__name__)
            + ". La lógica se mantiene en legacy/certificate_processor.py."
        )


def run_view() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CertificadosIcbfView()
    window.show()
    app.exec()
