from __future__ import annotations

from typing import Any

import pandas as pd
from PySide6 import QtCore, QtGui

from workflows.certificados_icbf.service import EDITABLE_FIELDS, CertificadosIcbfService, service


class RecordsTableModel(QtCore.QAbstractTableModel):
    """Qt adapter for the editable working DataFrame."""

    review_changed = QtCore.Signal(object)
    STATUS_COLUMN = "ESTADO"

    def __init__(
        self,
        records: pd.DataFrame,
        workflow_service: CertificadosIcbfService = service,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = workflow_service
        self._records = records.copy(deep=True).reset_index(drop=True)
        self._columns = [self.STATUS_COLUMN, *self._records.columns.tolist()]
        self._session = self._service.create_review_session(self._records)
        self._review = self._session.snapshot()

    @property
    def records(self) -> pd.DataFrame:
        return self._records.copy(deep=True)

    @property
    def review(self) -> dict[str, Any]:
        return self._review

    @property
    def review_session(self):
        return self._session

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._records)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._columns)

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        row, column = index.row(), self._columns[index.column()]
        row_review = self._review["rows"][row]

        if column == "INCLUIR" and role == QtCore.Qt.CheckStateRole:
            return QtCore.Qt.Checked if bool(self._records.iloc[row][column]) else QtCore.Qt.Unchecked
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if column == self.STATUS_COLUMN:
                return row_review["status"]
            if column == "INCLUIR":
                return ""
            value = self._records.iloc[row][column]
            return "" if pd.isna(value) else str(value)
        if role == QtCore.Qt.ToolTipRole:
            anomalies = row_review["anomalies"]
            detail = "\n".join(anomalies) if anomalies else row_review["status"]
            if column in EDITABLE_FIELDS:
                return f"Campo editable: doble clic para corregir.\n{detail}"
            return detail
        if role == QtCore.Qt.ForegroundRole:
            color = "#64748b" if row_review["status"] == "No incluido" else "#0f172a"
            return QtGui.QBrush(QtGui.QColor(color))
        if role == QtCore.Qt.BackgroundRole:
            if row_review["status"] == "No incluido":
                return QtGui.QBrush(QtGui.QColor("#f1f5f9"))
            if row_review["anomalies"]:
                return QtGui.QBrush(QtGui.QColor("#fff7ed"))
            if column in EDITABLE_FIELDS:
                return QtGui.QBrush(QtGui.QColor("#eff6ff"))
            return QtGui.QBrush(QtGui.QColor("#f0fdf4"))
        if role == QtCore.Qt.TextAlignmentRole:
            return QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
        return None

    def setData(self, index: QtCore.QModelIndex, value, role: int = QtCore.Qt.EditRole) -> bool:
        if not index.isValid():
            return False
        column = self._columns[index.column()]
        if column == "INCLUIR":
            if role not in (QtCore.Qt.CheckStateRole, QtCore.Qt.EditRole):
                return False
            included = value == QtCore.Qt.Checked if role == QtCore.Qt.CheckStateRole else bool(value)
            self._review = self._session.set_included(index.row(), included)
            self._records = self._session.records
        elif column in EDITABLE_FIELDS and role == QtCore.Qt.EditRole:
            updated = self._service.update_editable_field(
                self._records, index.row(), column, value
            )
            self._review = self._session.revalidate(updated)
            self._records = self._session.records
        else:
            return False
        self.dataChanged.emit(
            self.index(0, 0),
            self.index(self.rowCount() - 1, self.columnCount() - 1),
        )
        self.review_changed.emit(self._review)
        return True

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        flags = super().flags(index)
        if index.isValid() and self._columns[index.column()] == "INCLUIR":
            flags |= QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable
        elif index.isValid() and self._columns[index.column()] in EDITABLE_FIELDS:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section: int, orientation: QtCore.Qt.Orientation, role: int = QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return self._columns[section]
        return section + 1

    def categories_for_row(self, row: int) -> set[str]:
        return set(self._review["rows"][row]["categories"])

    def anomalies_for_row(self, row: int) -> list[str]:
        return list(self._review["rows"][row]["anomalies"])


class RecordsFilterProxyModel(QtCore.QSortFilterProxyModel):
    FILTERS = {"all", "valid", "duplicates", "invalid", "missing", "included", "excluded"}

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._category = "all"
        self.setDynamicSortFilter(True)

    def set_category(self, category: str) -> None:
        if category not in self.FILTERS:
            raise ValueError(f"Filtro desconocido: {category}")
        self.beginFilterChange()
        self._category = category
        self.endFilterChange(QtCore.QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
        if self._category == "all":
            return True
        model = self.sourceModel()
        return isinstance(model, RecordsTableModel) and self._category in model.categories_for_row(source_row)
