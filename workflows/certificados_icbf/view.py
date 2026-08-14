from __future__ import annotations

from pathlib import Path
from time import perf_counter

from PySide6 import QtCore, QtWidgets

from app.file_io import FileOperationError, open_folder, save_bytes_to_file
from app.logging_config import get_logger, safe_file_metadata
from workflows.certificados_icbf.models import RecordsFilterProxyModel, RecordsTableModel
from workflows.certificados_icbf.service import service


logger = get_logger("certificados_icbf")


class ExcelProcessorWorker(QtCore.QObject):
    succeeded = QtCore.Signal(object, object, str)
    failed = QtCore.Signal(str)
    finished = QtCore.Signal()

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path

    @QtCore.Slot()
    def run(self) -> None:
        started = perf_counter()
        logger.info("Procesamiento iniciado %s", safe_file_metadata(self.file_path))
        try:
            records, stats = service.read_and_clean_excel(self.file_path)
            email_text = service.build_email_text(records)
            logger.info(
                "Procesamiento finalizado registros=%s recibidos=%s excluidos=%s tiempo=%.3fs",
                len(records), stats["recibidos"], stats["excluidos"], perf_counter() - started,
            )
            self.succeeded.emit(records, stats, email_text)
        except ValueError:
            logger.warning("Procesamiento rechazado por formato o datos invalidos")
            self.failed.emit(
                "No fue posible procesar el archivo. Verifique que sea un Excel válido y contenga las columnas requeridas."
            )
        except Exception:
            logger.exception("Fallo inesperado durante procesamiento")
            self.failed.emit(
                "No fue posible procesar el archivo por un error inesperado. Puede volver a intentarlo."
            )
        finally:
            self.finished.emit()


class OutputGenerationWorker(QtCore.QObject):
    succeeded = QtCore.Signal(str, object)
    failed = QtCore.Signal(str, str)
    finished = QtCore.Signal()

    def __init__(self, output_type: str, records) -> None:
        super().__init__()
        self.output_type = output_type
        self.records = records.copy(deep=True)

    @QtCore.Slot()
    def run(self) -> None:
        started = perf_counter()
        logger.info("Generacion iniciada tipo=%s registros=%s", self.output_type, len(self.records))
        try:
            if self.output_type == "pdf":
                content = service.generate_pdf(self.records)
            elif self.output_type == "zip":
                content = service.generate_pdf_zip_by_unit(self.records)
            else:
                raise ValueError("Tipo de generación no compatible.")
            logger.info(
                "Generacion finalizada tipo=%s bytes=%s tiempo=%.3fs",
                self.output_type, len(content), perf_counter() - started,
            )
            self.succeeded.emit(self.output_type, content)
        except ValueError:
            logger.warning("Generacion bloqueada tipo=%s", self.output_type)
            self.failed.emit(
                self.output_type,
                "Los registros seleccionados todavía requieren revisión.",
            )
        except Exception:
            logger.exception("Fallo inesperado de generacion tipo=%s", self.output_type)
            self.failed.emit(
                self.output_type,
                "No fue posible generar la salida. Puede volver a intentarlo.",
            )
        finally:
            self.finished.emit()


class CertificadosIcbfView(QtWidgets.QWidget):
    activity_changed = QtCore.Signal(str)
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
        self._output_thread: QtCore.QThread | None = None
        self._output_worker: OutputGenerationWorker | None = None
        self._synchronous_busy = False
        self._email_is_current = False
        self._last_open_directory: Path | None = None
        self._last_save_directory: Path | None = None
        self._build_ui()

    @property
    def is_busy(self) -> bool:
        return (
            self._thread is not None
            or self._output_thread is not None
            or self._synchronous_busy
        )

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
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(8)
        layout.addWidget(self.progress)
        self._build_summary(layout)
        self.workspace = QtWidgets.QTabWidget()
        self.workspace.setVisible(False)
        layout.addWidget(self.workspace, 1)
        self._build_review_area()
        self._build_outputs()

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

    def _build_review_area(self) -> None:
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
            "QScrollBar:vertical { background: #e5e7eb; width: 15px; margin: 0; }"
            "QScrollBar::handle:vertical { background: #64748b; min-height: 32px; "
            "border-radius: 6px; margin: 2px; }"
            "QScrollBar::handle:vertical:hover { background: #334155; }"
            "QScrollBar:horizontal { background: #e5e7eb; height: 15px; margin: 0; }"
            "QScrollBar::handle:horizontal { background: #64748b; min-width: 32px; "
            "border-radius: 6px; margin: 2px; }"
            "QScrollBar::handle:horizontal:hover { background: #334155; }"
            "QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }"
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.setSortingEnabled(False)
        self.table.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
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
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([520, 90])
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
        self.workspace.addTab(self.review_widget, "2. Revisar registros")

    def _build_outputs(self) -> None:
        self.outputs_group = QtWidgets.QGroupBox("3. Generar archivos")
        output_layout = QtWidgets.QVBoxLayout(self.outputs_group)
        self.stage_label = QtWidgets.QLabel(
            "1. Cargar archivo  ✓    2. Revisar información    3. Generar archivos"
        )
        output_layout.addWidget(self.stage_label)

        actions = QtWidgets.QGridLayout()
        self.pdf_button = QtWidgets.QPushButton("Guardar PDF general")
        self.zip_button = QtWidgets.QPushButton("Guardar ZIP por unidad")
        self.duplicates_button = QtWidgets.QPushButton("Guardar reporte de duplicados")
        self.missing_button = QtWidgets.QPushButton("Guardar reporte de campos faltantes")
        self.pdf_button.clicked.connect(lambda: self._start_generation("pdf"))
        self.zip_button.clicked.connect(lambda: self._start_generation("zip"))
        self.duplicates_button.clicked.connect(lambda: self._save_report("duplicates"))
        self.missing_button.clicked.connect(lambda: self._save_report("missing"))
        for index, button in enumerate(
            [self.pdf_button, self.zip_button, self.duplicates_button, self.missing_button]
        ):
            actions.addWidget(button, index // 2, index % 2)
        output_layout.addLayout(actions)

        output_layout.addWidget(QtWidgets.QLabel("Texto sugerido para correo"))
        self.email_text = QtWidgets.QPlainTextEdit()
        self.email_text.setReadOnly(True)
        self.email_text.setMaximumHeight(125)
        output_layout.addWidget(self.email_text)
        email_actions = QtWidgets.QHBoxLayout()
        self.refresh_email_button = QtWidgets.QPushButton("Actualizar texto")
        self.refresh_email_button.clicked.connect(self._refresh_email_text)
        email_actions.addWidget(self.refresh_email_button)
        self.copy_email_button = QtWidgets.QPushButton("Copiar al portapapeles")
        self.copy_email_button.clicked.connect(self._copy_email_text)
        email_actions.addWidget(self.copy_email_button)
        email_actions.addStretch()
        output_layout.addLayout(email_actions)
        self.generation_status = QtWidgets.QLabel()
        self.generation_status.setWordWrap(True)
        output_layout.addWidget(self.generation_status)
        self.workspace.addTab(self.outputs_group, "3. Generar archivos")

    @QtCore.Slot()
    def _select_file(self) -> None:
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Seleccionar archivo Excel",
            str(self._last_open_directory or Path.home()),
            "Archivos Excel (*.xlsx *.xlsm *.xls)",
        )
        if not selected:
            logger.info("Seleccion de archivo cancelada")
            self.activity_changed.emit("Operación cancelada")
            return
        path = Path(selected)
        if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            logger.warning("Extension de entrada no permitida extension=%s", path.suffix.lower())
            QtWidgets.QMessageBox.warning(self, "Archivo no válido", "Selecciona un archivo Excel válido.")
            return
        self.file_path = path
        self._last_open_directory = path.parent
        logger.info("Archivo seleccionado %s", safe_file_metadata(path))
        self.file_label.setText(str(path))
        self.process_button.setEnabled(True)
        self.status.setText("Archivo listo para procesar.")
        self.activity_changed.emit("Archivo listo para procesar")
        self.summary_group.setVisible(False)
        self.workspace.setVisible(False)

    @QtCore.Slot()
    def _process_file(self) -> None:
        if self.file_path is None or self.is_busy:
            return
        self.process_button.setEnabled(False)
        self.status.setText("Procesando archivo…")
        self.progress.setVisible(True)
        self.activity_changed.emit("Procesando archivo…")
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

    @QtCore.Slot(object, object, str)
    def _show_results(self, records, stats: dict, email_text: str = "") -> None:
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
        self.workspace.setVisible(True)
        self.workspace.setCurrentWidget(self.review_widget)
        self.email_text.setPlainText(email_text or service.build_email_text(records))
        self._email_is_current = True
        self._review_changed(self.table_model.review)
        self.status.setText("Procesamiento completado. Revisa los registros y sus anomalías.")
        self.activity_changed.emit(f"{len(records)} registros procesados")

    @QtCore.Slot(object)
    def _review_changed(self, review: dict) -> None:
        if self.table_model is None or self.stats is None:
            return
        self.records = self.table_model.records
        if self.sender() is self.table_model:
            self._email_is_current = False
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
        self.continue_button.setText("Ir a generación")
        self.stage_label.setText(
            "1. Cargar archivo  ✓    2. Revisar información  ✓    3. Generar archivos  ←"
            if review["ready"]
            else "1. Cargar archivo  ✓    2. Revisar información  ←    3. Generar archivos"
        )
        self.pdf_button.setEnabled(bool(review["ready"]) and self._output_thread is None)
        self.zip_button.setEnabled(bool(review["ready"]) and self._output_thread is None)
        self.duplicates_button.setEnabled(bool(summary["reporte_duplicados"]))
        self.missing_button.setEnabled(bool(summary["reporte_faltantes"]))
        if self._email_is_current and self.records is not None:
            self._email_is_current = self.records.equals(self.table_model.records)
        if not self._email_is_current:
            self.generation_status.setText(
                "La selección cambió. Actualiza o copia el texto para reflejar los registros actuales."
            )
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
        self.workspace.setCurrentWidget(self.outputs_group)
        self.outputs_group.setFocus(QtCore.Qt.OtherFocusReason)
        self.generation_status.setText("Los datos están listos. Selecciona una salida para generarla.")

    def _start_generation(self, output_type: str) -> None:
        if self.is_busy:
            return
        if self.table_model is None or not self.table_model.review["ready"]:
            logger.warning("Intento de generacion sin registros listos tipo=%s", output_type)
            QtWidgets.QMessageBox.warning(
                self, "Generación bloqueada", "Los registros seleccionados todavía requieren revisión."
            )
            return
        self._set_generation_busy(True, output_type)
        self._output_thread = QtCore.QThread(self)
        self._output_worker = OutputGenerationWorker(output_type, self.table_model.records)
        self._output_worker.moveToThread(self._output_thread)
        self._output_thread.started.connect(self._output_worker.run)
        self._output_worker.succeeded.connect(self._generation_succeeded)
        self._output_worker.failed.connect(self._generation_failed)
        self._output_worker.finished.connect(self._output_thread.quit)
        self._output_worker.finished.connect(self._output_worker.deleteLater)
        self._output_thread.finished.connect(self._output_thread.deleteLater)
        self._output_thread.finished.connect(self._generation_finished)
        self._output_thread.start()

    @QtCore.Slot(str, object)
    def _generation_succeeded(self, output_type: str, content: bytes) -> None:
        self._request_save(content, output_type)

    @QtCore.Slot(str, str)
    def _generation_failed(self, output_type: str, technical_detail: str) -> None:
        self.generation_status.setText("La generación no pudo completarse. Los datos de revisión se conservaron.")
        self.activity_changed.emit("Error de generación; puede volver a intentarlo")
        QtWidgets.QMessageBox.critical(
            self,
            "No se pudo generar",
            technical_detail,
        )

    @QtCore.Slot()
    def _generation_finished(self) -> None:
        self._output_thread = None
        self._output_worker = None
        self.progress.setVisible(False)
        self.process_button.setEnabled(self.file_path is not None)
        if self.table_model is not None:
            self._review_changed(self.table_model.review)

    def _set_generation_busy(self, busy: bool, output_type: str = "") -> None:
        self.pdf_button.setEnabled(not busy and bool(self.table_model and self.table_model.review["ready"]))
        self.zip_button.setEnabled(not busy and bool(self.table_model and self.table_model.review["ready"]))
        self.duplicates_button.setEnabled(
            not busy and bool(self.table_model and self.table_model.review["summary"]["reporte_duplicados"])
        )
        self.missing_button.setEnabled(
            not busy and bool(self.table_model and self.table_model.review["summary"]["reporte_faltantes"])
        )
        self.process_button.setEnabled(not busy and self.file_path is not None)
        self.progress.setVisible(busy)
        if busy:
            description = "ZIP por unidad" if output_type == "zip" else output_type.upper()
            message = f"Generando {description}…"
            self.generation_status.setText(message)
            self.activity_changed.emit(message)

    def _save_report(self, report_type: str) -> None:
        if self.table_model is None or self.is_busy:
            return
        started = perf_counter()
        self._synchronous_busy = True
        self._set_generation_busy(True, "reporte")
        try:
            if report_type == "duplicates":
                content = service.generate_duplicates_report(self.table_model.review_session)
            else:
                content = service.generate_missing_fields_report(self.table_model.review_session)
            logger.info(
                "Reporte generado tipo=%s bytes=%s tiempo=%.3fs",
                report_type, len(content), perf_counter() - started,
            )
            self._request_save(content, report_type)
        except ValueError:
            logger.warning("Reporte no disponible tipo=%s", report_type)
            self.generation_status.setText("No existen registros para este reporte.")
            QtWidgets.QMessageBox.critical(
                self, "Reporte no disponible", "No existen registros para generar este reporte."
            )
        except Exception:
            logger.exception("Fallo inesperado preparando reporte tipo=%s", report_type)
            self.generation_status.setText("No fue posible preparar el reporte. Los datos se conservaron.")
            QtWidgets.QMessageBox.critical(
                self, "No se pudo generar", "No fue posible preparar el reporte. Puedes volver a intentarlo."
            )
        finally:
            self._synchronous_busy = False
            self._set_generation_busy(False)

    def _request_save(self, content: bytes, output_type: str) -> None:
        if self.file_path is None:
            return
        filename = service.suggested_filename(self.file_path, output_type)
        filters = {
            "pdf": "Archivo PDF (*.pdf)", "zip": "Archivo ZIP (*.zip)",
            "duplicates": "Archivo Excel (*.xlsx)", "missing": "Archivo Excel (*.xlsx)",
        }
        destination, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Guardar archivo",
            str((self._last_save_directory or self.file_path.parent) / filename),
            filters[output_type],
        )
        if not destination:
            self.generation_status.setText("Guardado cancelado por el usuario.")
            self.activity_changed.emit("Operación cancelada")
            logger.info("Guardado cancelado tipo=%s", output_type)
            return
        try:
            saved_path = save_bytes_to_file(destination, content)
        except (FileOperationError, FileNotFoundError, ValueError):
            logger.warning("Guardado rechazado tipo=%s", output_type)
            self.generation_status.setText("No fue posible guardar el archivo. Los datos se conservaron para reintentar.")
            QtWidgets.QMessageBox.critical(
                self, "No se pudo guardar", "No fue posible escribir el archivo en la ubicación seleccionada."
            )
            return
        except Exception:
            logger.exception("Fallo inesperado guardando salida tipo=%s", output_type)
            self.generation_status.setText("No fue posible guardar el archivo. Los datos se conservaron.")
            QtWidgets.QMessageBox.critical(
                self, "No se pudo guardar", "Ocurrió un error inesperado al guardar. Puede volver a intentarlo."
            )
            return
        self._last_save_directory = saved_path.parent
        logger.info("Archivo guardado tipo=%s extension=%s bytes=%s", output_type, saved_path.suffix, len(content))
        self.generation_status.setText(f"Archivo guardado correctamente: {saved_path}")
        self.activity_changed.emit(f"{output_type.upper()} guardado correctamente")
        open_result = QtWidgets.QMessageBox.question(
            self,
            "Guardado completo",
            "Archivo guardado correctamente.\n\n¿Desea abrir la carpeta de salida?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No,
        )
        if open_result == QtWidgets.QMessageBox.Yes:
            try:
                open_folder(saved_path.parent)
            except (FileOperationError, FileNotFoundError):
                logger.warning("No fue posible abrir carpeta de salida")
                QtWidgets.QMessageBox.warning(
                    self, "No se pudo abrir", "No fue posible abrir la carpeta de salida."
                )

    def _copy_email_text(self) -> None:
        if self.table_model is None:
            return
        if not self._email_is_current:
            self._refresh_email_text()
        QtWidgets.QApplication.clipboard().setText(self.email_text.toPlainText())
        self.generation_status.setText("Texto sugerido copiado al portapapeles.")

    def _refresh_email_text(self) -> None:
        if self.table_model is None:
            return
        try:
            self.email_text.setPlainText(service.build_email_text(self.table_model.records))
            self._email_is_current = True
            self.generation_status.setText("Texto sugerido actualizado.")
        except Exception as error:
            self.generation_status.setText(f"Detalle técnico: {error}")
            QtWidgets.QMessageBox.critical(
                self, "No se pudo actualizar", "No fue posible actualizar el texto sugerido."
            )

    @QtCore.Slot(str)
    def _show_error(self, message: str) -> None:
        self.status.setText("No fue posible procesar el archivo.")
        self.activity_changed.emit("Error de procesamiento; puede volver a intentarlo")
        QtWidgets.QMessageBox.critical(self, "Error al procesar", message)

    @QtCore.Slot()
    def _processing_finished(self) -> None:
        self.process_button.setEnabled(self.file_path is not None)
        self.progress.setVisible(False)
        self._thread = None
        self._worker = None


def run_view() -> None:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    window = CertificadosIcbfView()
    window.show()
    app.exec()
