from __future__ import annotations

import logging

from PySide6 import QtCore, QtGui, QtWidgets

from app.logging_config import configure_logging, install_exception_hook
from app.workflow_contract import WorkflowDefinition
from app.workflow_registry import WorkflowRegistry, workflow_registry
from config.resources import CORPORATE_LOGO_PATH
from config.settings import APP_NAME
from version import APP_VERSION

logger = logging.getLogger(__name__)


class HomeView(QtWidgets.QWidget):
    workflow_requested = QtCore.Signal(str)

    def __init__(self, workflows: tuple[WorkflowDefinition, ...]) -> None:
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

        title = QtWidgets.QLabel(APP_NAME)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 24px; font-weight: 600;")
        layout.addWidget(title)
        version = QtWidgets.QLabel(f"Versión {APP_VERSION}")
        version.setAlignment(QtCore.Qt.AlignCenter)
        version.setStyleSheet("color: #64748b;")
        layout.addWidget(version)
        layout.addSpacing(24)

        for definition in workflows:
            button = QtWidgets.QPushButton(f"Abrir {definition.name}")
            button.setToolTip(definition.description)
            button.setMinimumHeight(46)
            button.clicked.connect(
                lambda checked=False, workflow_id=definition.id: self.workflow_requested.emit(
                    workflow_id
                )
            )
            layout.addWidget(button)
        layout.addStretch()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, registry: WorkflowRegistry = workflow_registry) -> None:
        super().__init__()
        self.registry = registry
        self.workflow_definitions = registry.enabled()
        self.workflow_views: dict[str, QtWidgets.QWidget] = {}
        self.navigation_workflow_ids: list[str | None] = [None]

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

        root = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navigation = QtWidgets.QListWidget()
        self.navigation.setFixedWidth(220)
        self.navigation.addItem("Inicio")
        for definition in self.workflow_definitions:
            self.navigation.addItem(definition.name)
            self.navigation_workflow_ids.append(definition.id)
        self.navigation.setCurrentRow(0)
        self.navigation.currentRowChanged.connect(self._show_page)
        layout.addWidget(self.navigation)

        self.pages = QtWidgets.QStackedWidget()
        self.home = HomeView(self.workflow_definitions)
        self.home.workflow_requested.connect(self.open_workflow)
        self.pages.addWidget(self.home)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Listo")
        self._fit_restored_window_to_available_area()

    def _fit_restored_window_to_available_area(self) -> None:
        """Size and center the restored window inside the usable desktop area."""
        screen = self.screen() or QtWidgets.QApplication.primaryScreen()
        if screen is None:
            self.resize(1180, 700)
            return
        available = screen.availableGeometry()
        margin = 24
        width = min(1180, max(760, available.width() - margin * 2))
        height = min(700, max(560, available.height() - margin * 2))
        self.resize(width, height)
        self.move(
            available.x() + (available.width() - width) // 2,
            available.y() + (available.height() - height) // 2,
        )

    @QtCore.Slot(str)
    def open_workflow(self, workflow_id: str) -> None:
        try:
            navigation_index = self.navigation_workflow_ids.index(workflow_id)
        except ValueError:
            logger.warning("workflow=%s operation=navigate status=unknown", workflow_id)
            return
        self.navigation.setCurrentRow(navigation_index)

    @QtCore.Slot(int)
    def _show_page(self, navigation_index: int) -> None:
        if navigation_index == 0:
            self.pages.setCurrentWidget(self.home)
            return
        if not 0 <= navigation_index < len(self.navigation_workflow_ids):
            return
        workflow_id = self.navigation_workflow_ids[navigation_index]
        if workflow_id is None:
            return
        view = self._get_or_create_workflow_view(workflow_id)
        if view is not None:
            self.pages.setCurrentWidget(view)

    def _get_or_create_workflow_view(self, workflow_id: str) -> QtWidgets.QWidget | None:
        if workflow_id in self.workflow_views:
            return self.workflow_views[workflow_id]
        definition = self.registry.get(workflow_id)
        try:
            view = definition.create_view()
        except Exception:
            logger.exception("workflow=%s operation=load status=failed", workflow_id)
            QtWidgets.QMessageBox.critical(
                self,
                "No fue posible abrir el flujo",
                f"No fue posible cargar {definition.name}. Puede volver a Inicio e intentarlo de nuevo.",
            )
            self.navigation.blockSignals(True)
            self.navigation.setCurrentRow(0)
            self.navigation.blockSignals(False)
            self.pages.setCurrentWidget(self.home)
            return None
        activity_signal = getattr(view, "activity_changed", None)
        if activity_signal is not None:
            activity_signal.connect(self.statusBar().showMessage)
        self.workflow_views[workflow_id] = view
        self.pages.addWidget(view)
        logger.info("workflow=%s operation=load status=completed", workflow_id)
        return view

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if any(bool(getattr(view, "is_busy", False)) for view in self.workflow_views.values()):
            QtWidgets.QMessageBox.warning(
                self,
                "Operación en progreso",
                "Hay una operación en progreso. Espere a que finalice antes de cerrar la aplicación.",
            )
            event.ignore()
            return
        event.accept()


def run_app() -> None:
    app_logger = configure_logging()
    app_logger.info("Aplicacion iniciada version=%s", APP_VERSION)
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    install_exception_hook(
        lambda message: QtWidgets.QMessageBox.critical(None, "Error inesperado", message)
    )
    window = MainWindow()
    window.show()
    app.exec()
