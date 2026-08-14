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
