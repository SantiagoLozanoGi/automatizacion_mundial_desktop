from __future__ import annotations

from io import BytesIO

import pandas as pd
from PySide6 import QtCore, QtGui

from workflows.certificados_icbf.models import RecordsFilterProxyModel, RecordsTableModel
from workflows.certificados_icbf.service import CertificadosIcbfService


def build_source() -> BytesIO:
    frame = pd.DataFrame(
        [
            ["Ana", None, "Díaz", None, "123", "01/01/2010", "Bogotá", "INGRESO"],
            ["Luis", None, "Pérez", None, "456", "02/02/2011", "Cali", "IN"],
        ],
        columns=[
            "Primer Nombre", "Segundo Nombre", "Primer Apellido", "Segundo Apellido",
            "Número de Identificación", "Fecha de Nacimiento", "UNIDADES", "Tipo de Novedad",
        ],
    )
    output = BytesIO()
    frame.to_excel(output, index=False)
    output.seek(0)
    return output


def build_duplicate_model() -> RecordsTableModel:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())
    records.loc[1, "DOCUMENTO"] = records.loc[0, "DOCUMENTO"]
    return RecordsTableModel(records, service)


def test_model_changes_include_and_preserves_all_source_rows() -> None:
    model = build_duplicate_model()
    include_column = model._columns.index("INCLUIR")

    assert model.setData(model.index(1, include_column), QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)

    assert model.rowCount() == 2
    assert bool(model.records.loc[1, "INCLUIR"]) is False
    assert model.review["ready"] is True


def test_proxy_filters_without_removing_records() -> None:
    model = build_duplicate_model()
    proxy = RecordsFilterProxyModel()
    proxy.setSourceModel(model)

    proxy.set_category("duplicates")
    assert proxy.rowCount() == 2
    proxy.set_category("valid")
    assert proxy.rowCount() == 0
    proxy.set_category("all")
    assert proxy.rowCount() == 2
    assert model.rowCount() == 2


def test_proxy_reacts_to_selection_and_filters_excluded() -> None:
    model = build_duplicate_model()
    proxy = RecordsFilterProxyModel()
    proxy.setSourceModel(model)
    include_column = model._columns.index("INCLUIR")

    model.setData(model.index(1, include_column), QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)
    proxy.set_category("excluded")

    assert proxy.rowCount() == 1
    assert proxy.mapToSource(proxy.index(0, 0)).row() == 1
    assert model.rowCount() == 2


def test_model_uses_explicit_readable_foreground_and_background() -> None:
    model = build_duplicate_model()
    index = model.index(0, 1)

    foreground = model.data(index, QtCore.Qt.ForegroundRole)
    background = model.data(index, QtCore.Qt.BackgroundRole)

    assert isinstance(foreground, QtGui.QBrush)
    assert foreground.color().name() == "#0f172a"
    assert isinstance(background, QtGui.QBrush)
    assert background.color().lightness() > foreground.color().lightness()
