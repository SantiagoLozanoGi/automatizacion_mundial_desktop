from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from workflows.certificados_icbf.service import service


class ExcelProcessorWorker(QtCore.QObject):
    succeeded = QtCore.Signal(object, object, object)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    @QtCore.Slot()
    def run(self) -> None:
        try:
            records, stats = service.read_and_clean_excel(self.file_path)
            summary = service.validation_summary(records)
            self.succeeded.emit(records, stats, summary)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class CertificadosIcbfView(QtWidgets.QWidget):
    ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}

    def __init__(self) -> None:
        super().__init__()
        self.file_path: Path | None = None
        self.records = None
        self._thread: QtCore.QThread | None = None
        self._worker: ExcelProcessorWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        title = QtWidgets.QLabel("Certificados ICBF")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel("Selecciona y procesa el archivo de novedades de ingreso."))

        file_row = QtWidgets.QHBoxLayout()
        self.file_label = QtWidgets.QLineEdit()
        self.file_label.setReadOnly(True)
        self.file_label.setPlaceholderText("Ningún archivo seleccionado")
        file_row.addWidget(self.file_label, 1)
        select_button = QtWidgets.QPushButton("Seleccionar Excel")
        select_button.clicked.connect(self._select_file)
        file_row.addWidget(select_button)
        layout.addLayout(file_row)

        self.process_button = QtWidgets.QPushButton("Procesar archivo")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._process_file)
        layout.addWidget(self.process_button)
        self.status = QtWidgets.QLabel("Esperando un archivo Excel.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.summary_group = QtWidgets.QGroupBox("Resumen de validación")
        summary_layout = QtWidgets.QGridLayout(self.summary_group)
        labels = [
            ("recibidos", "Registros recibidos"),
            ("procesables", "Registros procesables"),
            ("seleccionados", "Seleccionados (INCLUIR)"),
            ("duplicados", "Filas duplicadas"),
            ("invalidos", "Documentos inválidos"),
            ("faltantes", "Campos obligatorios faltantes"),
            ("validos", "Válidos para certificados"),
        ]
        self.metrics: dict[str, QtWidgets.QLabel] = {}
        for index, (key, text) in enumerate(labels):
            caption = QtWidgets.QLabel(text)
            value = QtWidgets.QLabel("—")
            value.setStyleSheet("font-size: 20px; font-weight: 600;")
            row, column = divmod(index, 4)
            cell = QtWidgets.QVBoxLayout()
            cell.addWidget(caption)
            cell.addWidget(value)
            summary_layout.addLayout(cell, row, column)
            self.metrics[key] = value
        self.summary_group.setVisible(False)
        layout.addWidget(self.summary_group)
        layout.addStretch()

    @QtCore.Slot()
    def _select_file(self) -> None:
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel", "", "Archivos Excel (*.xlsx *.xlsm *.xls)"
        )
        if not selected:
            return
        path = Path(selected)
        if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            QtWidgets.QMessageBox.warning(self, "Archivo no válido", "Selecciona un archivo Excel válido.")
            return
        self.file_path = path
        self.file_label.setText(str(path))
        self.process_button.setEnabled(True)
        self.status.setText("Archivo listo para procesar.")
        self.summary_group.setVisible(False)

    @QtCore.Slot()
    def _process_file(self) -> None:
        if self.file_path is None:
            return
        self.process_button.setEnabled(False)
        self.status.setText("Procesando archivo…")
        self._thread = QtCore.QThread(self)
        self._worker = ExcelProcessorWorker(self.file_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.succeeded.connect(self._show_results)
        self._worker.failed.connect(self._show_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._processing_finished)
        self._thread.start()

    @QtCore.Slot(object, object, object)
    def _show_results(self, records, stats: dict, summary: dict) -> None:
        self.records = records
        values = {
            "recibidos": stats["recibidos"],
            "procesables": stats["ingresos"],
            "seleccionados": summary["registros_activos"],
            "duplicados": summary["filas_duplicadas"],
            "invalidos": summary["documentos_invalidos"],
            "faltantes": summary["campos_informativos"],
            "validos": summary["registros_validos"],
        }
        for key, value in values.items():
            self.metrics[key].setText(str(value))
        self.summary_group.setVisible(True)
        self.status.setText("Procesamiento completado. Revisa el resumen de validación.")

    @QtCore.Slot(str)
    def _show_error(self, message: str) -> None:
        self.status.setText("No fue posible procesar el archivo.")
        QtWidgets.QMessageBox.critical(self, "Error al procesar", message)

    @QtCore.Slot()
    def _processing_finished(self) -> None:
        self.process_button.setEnabled(self.file_path is not None)
        self._thread = None
        self._worker = None


def run_view() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CertificadosIcbfView()
    window.show()
    app.exec()
