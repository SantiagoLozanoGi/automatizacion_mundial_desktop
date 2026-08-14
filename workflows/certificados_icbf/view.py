from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from workflows.certificados_icbf.models import RecordsFilterProxyModel, RecordsTableModel
from workflows.certificados_icbf.service import service


class ExcelProcessorWorker(QtCore.QObject):
    succeeded = QtCore.Signal(object, object)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    @QtCore.Slot()
    def run(self) -> None:
        try:
            records, stats = service.read_and_clean_excel(self.file_path)
            self.succeeded.emit(records, stats)
        except Exception as error:
            self.failed.emit(str(error))
        finally:
            self.finished.emit()


class CertificadosIcbfView(QtWidgets.QWidget):
    ALLOWED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}
    FILTERS = [
        ("Todos", "all"),
        ("Válidos", "valid"),
        ("Duplicados", "duplicates"),
        ("Documentos inválidos", "invalid"),
        ("Campos faltantes", "missing"),
        ("Incluidos", "included"),
        ("No incluidos", "excluded"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.file_path: Path | None = None
        self.records = None
        self.stats: dict | None = None
        self.table_model: RecordsTableModel | None = None
        self.proxy_model: RecordsFilterProxyModel | None = None
        self._thread: QtCore.QThread | None = None
        self._worker: ExcelProcessorWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        title = QtWidgets.QLabel("Certificados ICBF")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)
        layout.addWidget(QtWidgets.QLabel("Procesa el Excel y revisa los registros antes de generar certificados."))

        file_row = QtWidgets.QHBoxLayout()
        self.file_label = QtWidgets.QLineEdit()
        self.file_label.setReadOnly(True)
        self.file_label.setPlaceholderText("Ningún archivo seleccionado")
        file_row.addWidget(self.file_label, 1)
        select_button = QtWidgets.QPushButton("Seleccionar Excel")
        select_button.clicked.connect(self._select_file)
        file_row.addWidget(select_button)
        self.process_button = QtWidgets.QPushButton("Procesar archivo")
        self.process_button.setEnabled(False)
        self.process_button.clicked.connect(self._process_file)
        file_row.addWidget(self.process_button)
        layout.addLayout(file_row)

        self.status = QtWidgets.QLabel("Esperando un archivo Excel.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self._build_summary(layout)
        self._build_review_area(layout)

    def _build_summary(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        self.summary_group = QtWidgets.QGroupBox("Resumen de validación")
        summary_layout = QtWidgets.QGridLayout(self.summary_group)
        labels = [
            ("recibidos", "Recibidos"), ("procesables", "Procesables"),
            ("seleccionados", "Seleccionados"), ("no_seleccionados", "No seleccionados"),
            ("duplicados", "Duplicados"), ("invalidos", "Docs. inválidos"),
            ("faltantes", "Campos faltantes"), ("validos", "Válidos seleccionados"),
        ]
        self.metrics: dict[str, QtWidgets.QLabel] = {}
        for index, (key, text) in enumerate(labels):
            caption = QtWidgets.QLabel(text)
            value = QtWidgets.QLabel("—")
            value.setStyleSheet("font-size: 18px; font-weight: 600;")
            cell = QtWidgets.QVBoxLayout()
            cell.addWidget(caption)
            cell.addWidget(value)
            row, column = divmod(index, 4)
            summary_layout.addLayout(cell, row, column)
            self.metrics[key] = value
        self.summary_group.setVisible(False)
        parent_layout.addWidget(self.summary_group)

    def _build_review_area(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        self.review_widget = QtWidgets.QWidget()
        review_layout = QtWidgets.QVBoxLayout(self.review_widget)
        review_layout.setContentsMargins(0, 0, 0, 0)
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("Mostrar:"))
        self.filter_combo = QtWidgets.QComboBox()
        for label, category in self.FILTERS:
            self.filter_combo.addItem(label, category)
        self.filter_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.filter_combo)
        self.visible_count = QtWidgets.QLabel()
        filter_row.addWidget(self.visible_count)
        filter_row.addStretch()
        review_layout.addLayout(filter_row)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.table = QtWidgets.QTableView()
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(
            "QTableView { background: #ffffff; color: #0f172a; gridline-color: #cbd5e1; }"
            "QTableView::item { color: #0f172a; padding: 3px; }"
            "QTableView::item:selected { background: #2563eb; color: #ffffff; }"
            "QHeaderView::section { background: #e2e8f0; color: #0f172a; "
            "font-weight: 600; padding: 5px; border: 1px solid #cbd5e1; }"
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(145)
        self.table.horizontalHeader().setStretchLastSection(True)
        splitter.addWidget(self.table)

        detail_group = QtWidgets.QGroupBox("Detalle del registro seleccionado")
        detail_layout = QtWidgets.QVBoxLayout(detail_group)
        self.detail = QtWidgets.QLabel("Selecciona una fila para consultar su estado.")
        self.detail.setWordWrap(True)
        self.detail.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        detail_layout.addWidget(self.detail)
        splitter.addWidget(detail_group)
        splitter.setSizes([360, 100])
        review_layout.addWidget(splitter, 1)

        footer = QtWidgets.QHBoxLayout()
        self.workflow_status = QtWidgets.QLabel("Estado del archivo: pendiente")
        self.workflow_status.setStyleSheet("font-weight: 600;")
        footer.addWidget(self.workflow_status, 1)
        self.continue_button = QtWidgets.QPushButton("Continuar a generación")
        self.continue_button.setEnabled(False)
        self.continue_button.clicked.connect(self._continue_to_generation)
        footer.addWidget(self.continue_button)
        review_layout.addLayout(footer)
        self.blocking_reason = QtWidgets.QLabel()
        self.blocking_reason.setWordWrap(True)
        review_layout.addWidget(self.blocking_reason)
        self.review_widget.setVisible(False)
        parent_layout.addWidget(self.review_widget, 1)

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
        self.review_widget.setVisible(False)

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

    @QtCore.Slot(object, object)
    def _show_results(self, records, stats: dict) -> None:
        self.records = records.copy(deep=True)
        self.stats = stats
        self.table_model = RecordsTableModel(self.records)
        self.proxy_model = RecordsFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.table_model)
        self.table.setModel(self.proxy_model)
        self.table_model.review_changed.connect(self._review_changed)
        self.table.selectionModel().currentRowChanged.connect(self._show_row_detail)
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 72)
        self.filter_combo.setCurrentIndex(0)
        self.summary_group.setVisible(True)
        self.review_widget.setVisible(True)
        self._review_changed(self.table_model.review)
        self.status.setText("Procesamiento completado. Revisa los registros y sus anomalías.")

    @QtCore.Slot(object)
    def _review_changed(self, review: dict) -> None:
        if self.table_model is None or self.stats is None:
            return
        self.records = self.table_model.records
        summary = review["summary"]
        values = {
            "recibidos": self.stats["recibidos"], "procesables": self.stats["ingresos"],
            "seleccionados": summary["registros_activos"],
            "no_seleccionados": summary["no_seleccionados"],
            "duplicados": summary["filas_duplicadas"],
            "invalidos": summary["documentos_invalidos"],
            "faltantes": summary["campos_informativos"],
            "validos": summary["registros_validos"],
        }
        for key, value in values.items():
            self.metrics[key].setText(str(value))
        self.workflow_status.setText(f"Estado del archivo: {review['status']}")
        self.blocking_reason.setText(review["blocking_reason"])
        self.continue_button.setEnabled(bool(review["ready"]))
        if self.proxy_model is not None:
            self.proxy_model.set_category(self.filter_combo.currentData())
            self._update_visible_count()
        current = self.table.currentIndex()
        if current.isValid():
            self._show_row_detail(current, QtCore.QModelIndex())

    @QtCore.Slot(int)
    def _apply_filter(self, _index: int) -> None:
        if self.proxy_model is not None:
            self.proxy_model.set_category(self.filter_combo.currentData())
            self._update_visible_count()

    def _update_visible_count(self) -> None:
        if self.proxy_model is not None and self.table_model is not None:
            self.visible_count.setText(f"{self.proxy_model.rowCount()} de {self.table_model.rowCount()} registros")

    @QtCore.Slot(QtCore.QModelIndex, QtCore.QModelIndex)
    def _show_row_detail(self, current: QtCore.QModelIndex, _previous: QtCore.QModelIndex) -> None:
        if not current.isValid() or self.proxy_model is None or self.table_model is None:
            self.detail.setText("Selecciona una fila para consultar su estado.")
            return
        source_row = self.proxy_model.mapToSource(current).row()
        row_review = self.table_model.review["rows"][source_row]
        messages = row_review["anomalies"] or ["El registro no presenta anomalías bloqueantes."]
        if row_review["status"] == "No incluido":
            messages = ["El registro está desmarcado en INCLUIR."]
        self.detail.setText(f"Estado: {row_review['status']}\n" + "\n".join(f"• {item}" for item in messages))

    @QtCore.Slot()
    def _continue_to_generation(self) -> None:
        QtWidgets.QMessageBox.information(
            self, "Datos listos", "Los registros seleccionados están listos. La generación estará disponible en v0.3.0."
        )

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
