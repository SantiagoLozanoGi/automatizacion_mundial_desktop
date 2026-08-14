from __future__ import annotations

from io import BytesIO
import zipfile

import pandas as pd
from pypdf import PdfReader

from workflows.certificados_icbf.service import CertificadosIcbfService


def build_source() -> BytesIO:
    frame = pd.DataFrame(
        [
            ["Ana", None, "Díaz", None, "123", "01/01/2010", "Bogotá", "INGRESO"],
            ["Luis", "Alberto", "Pérez", None, "456", "02/02/2011", "Cali", "IN"],
        ],
        columns=[
            "Primer Nombre",
            "Segundo Nombre",
            "Primer Apellido",
            "Segundo Apellido",
            "Número de Identificación",
            "Fecha de Nacimiento",
            "UNIDADES",
            "Tipo de Novedad",
        ],
    )
    output = BytesIO()
    frame.to_excel(output, index=False)
    output.seek(0)
    return output


def test_service_processes_and_summarizes_excel() -> None:
    service = CertificadosIcbfService()

    records, stats = service.read_and_clean_excel(build_source())
    summary = service.validation_summary(records)

    assert stats == {"recibidos": 2, "ingresos": 2, "excluidos": 0}
    assert summary["registros_activos"] == 2
    assert summary["registros_validos"] == 2
    assert summary["blocking"] is False
    assert len(service.final_records(records)) == 2


def test_service_generates_pdf_and_zip_with_configured_logo() -> None:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())

    pdf_bytes = service.generate_pdf(records)
    zip_bytes = service.generate_pdf_zip_by_unit(records)

    assert pdf_bytes.startswith(b"%PDF")
    assert len(PdfReader(BytesIO(pdf_bytes)).pages) == 1
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        assert sorted(archive.namelist()) == ["Bogotá.pdf", "Cali.pdf"]
        assert all(archive.read(name).startswith(b"%PDF") for name in archive.namelist())


def test_service_exposes_reports_and_email_text() -> None:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())
    validation = service.validate_records(records)

    excel_bytes = service.dataframe_to_excel_bytes(
        {"Duplicados": validation["duplicates"], "Faltantes": validation["missing_report"]}
    )
    email_text = service.build_email_text(records)

    assert excel_bytes.startswith(b"PK")
    assert "Se procesaron 2 registros" in email_text


def test_service_updates_include_without_mutating_original() -> None:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())

    updated = service.set_included(records, 0, False)

    assert bool(records.loc[0, "INCLUIR"]) is True
    assert bool(updated.loc[0, "INCLUIR"]) is False
    assert service.validation_summary(updated)["registros_activos"] == 1


def test_service_reports_row_anomalies_and_ready_state() -> None:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())
    records.loc[1, "DOCUMENTO"] = records.loc[0, "DOCUMENTO"]

    review = service.review_records(records)

    assert review["ready"] is False
    assert review["status"] == "Requiere revisión"
    assert review["summary"]["filas_duplicadas"] == 2
    assert all("duplicates" in review["rows"][row]["categories"] for row in (0, 1))
    assert "Documento duplicado" in review["rows"][0]["anomalies"][0]

    updated = service.set_included(records, 1, False)
    ready_review = service.review_records(updated)
    assert ready_review["ready"] is True
    assert ready_review["summary"]["registros_activos"] == 1
    assert ready_review["summary"]["no_seleccionados"] == 1
    assert ready_review["rows"][1]["status"] == "No incluido"


def test_service_reports_invalid_and_missing_fields() -> None:
    service = CertificadosIcbfService()
    records, _ = service.read_and_clean_excel(build_source())
    records.loc[0, "DOCUMENTO"] = "ABC"
    records.loc[0, "UNIDADES"] = ""

    row_review = service.review_records(records)["rows"][0]

    assert row_review["categories"] == {"included", "invalid", "missing"}
    assert any("Documento inválido" in item for item in row_review["anomalies"])
    assert any("UNIDADES" in item for item in row_review["anomalies"])


def test_review_session_reuses_validation_and_revalidates_business_edits(monkeypatch) -> None:
    import workflows.certificados_icbf.service as service_module

    workflow_service = CertificadosIcbfService()
    records, _ = workflow_service.read_and_clean_excel(build_source())
    real_validate = service_module.validate_records
    calls = 0

    def counted_validate(frame):
        nonlocal calls
        calls += 1
        return real_validate(frame)

    monkeypatch.setattr(service_module, "validate_records", counted_validate)
    session = workflow_service.create_review_session(records)
    initial_anomalies = session.snapshot()["rows"][0]["anomalies"]
    session.set_included(0, False)
    session.set_included(0, True)

    assert calls == 1
    assert session.snapshot()["rows"][0]["anomalies"] == initial_anomalies

    edited = session.records
    edited.loc[0, "DOCUMENTO"] = "INVALIDO"
    refreshed = session.revalidate(edited)
    assert calls == 2
    assert "invalid" in refreshed["rows"][0]["categories"]
