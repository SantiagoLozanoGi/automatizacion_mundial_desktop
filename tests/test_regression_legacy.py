from __future__ import annotations

from io import BytesIO

import pandas as pd

from pypdf import PdfReader

from workflows.certificados_icbf.legacy.certificate_processor import (
    InputFormatError,
    _paginate,
    final_records,
    generate_pdf,
    generate_pdf_zip_by_unit,
    read_and_clean_excel,
    validate_records,
)


def build_source(rows):
    columns = [
        "Primer Nombre",
        "Segundo Nombre",
        "Primer Apellido",
        "Segundo Apellido",
        "Número de Identificación",
        "Fecha de  Nacimiento (dd/mm/aaaa)",
        "UNIDADES",
        "Tipo de Novedad",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    output = BytesIO()
    frame.to_excel(output, index=False)
    output.seek(0)
    return output


def test_validation_and_pdf():
    source = build_source([
        ["Ana", None, "Díaz", None, "100", "01/01/2010", "Bogotá", "INGRESO"],
        ["Luis", "NA", "Pérez", "NA", "100", "02/02/2011", "Bogotá", "IN"],
        ["Eva", None, "Rojas", None, None, "03/03/2012", "Cali", "INGRESO"],
        ["No", "Pasa", "Esta", "Fila", "999", "04/04/2013", "Cali", "EX"],
    ])
    records, stats = read_and_clean_excel(source)
    assert stats == {"recibidos": 4, "ingresos": 3, "excluidos": 1}
    assert set(records["SEGUNDO NOMBRE"]) == {"NA"}
    assert records.loc[0, "DOCUMENTO"] == "0000000100"
    validation = validate_records(records)
    assert validation["blocking"] is True
    assert len(validation["duplicates"]) == 2
    assert len(validation["missing_document"]) == 1

    records.loc[1, "DOCUMENTO"] = "101"
    records.loc[2, "INCLUIR"] = False
    validation = validate_records(records)
    assert validation["blocking"] is False
    final = final_records(records)
    assert final["UNIDADES"].tolist() == ["Bogotá", "Bogotá"]
    pdf = generate_pdf(records)
    assert pdf.startswith(b"%PDF")
    page = PdfReader(BytesIO(pdf)).pages[0]
    assert float(page.mediabox.height) > float(page.mediabox.width)

    zip_bytes = generate_pdf_zip_by_unit(records)
    assert zip_bytes[:2] == b"PK"


def test_reports_only_ingresos_and_required_fields():
    source = build_source([
        ["Ana", None, "Díaz", None, "123", "01/01/2010", "Bogotá", "INGRESO"],
        [None, "NA", "Pérez", "NA", "456", None, "", "IN"],
        [None, None, None, None, None, None, None, "EX"],
    ])
    records, _ = read_and_clean_excel(source)
    validation = validate_records(records)

    assert len(records) == 2
    assert records.loc[0, "DOCUMENTO"] == "0000000123"
    assert records.loc[1, "DOCUMENTO"] == "0000000456"
    assert len(validation["missing_report"]) == 1
    missing_row = validation["missing_report"].iloc[0]
    assert "CAMPOS OBLIGATORIOS FALTANTES" in missing_row
    assert missing_row["DOCUMENTO"] == "0000000456"
    assert missing_row["PRIMER NOMBRE"] == ""
    assert missing_row["FECHA DE NACIMIENTO"] == ""
    assert missing_row["UNIDADES"] == ""
    missing = missing_row["CAMPOS OBLIGATORIOS FALTANTES"]
    assert set(missing.split(", ")) == {
        "PRIMER NOMBRE",
        "FECHA DE NACIMIENTO",
        "UNIDADES",
    }
    assert "SEGUNDO NOMBRE" not in missing
    assert "SEGUNDO APELLIDO" not in missing


def test_accepts_second_surname_when_first_surname_missing():
    source = build_source([
        ["Ana", None, None, "Gómez", "123", "01/01/2010", "Bogotá", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)
    validation = validate_records(records)

    assert len(validation["missing_report"]) == 0
    assert validation["blocking"] is False


def test_invalid_document_blocks_pdf():
    source = build_source([
        ["Ana", None, "Díaz", None, "ABC123", "01/01/2010", "Bogotá", "INGRESO"],
        ["Eva", None, "Rojas", None, "12345678901", "03/03/2012", "Cali", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)
    validation = validate_records(records)
    assert validation["blocking"] is True
    assert len(validation["invalid_document"]) == 2


def test_city_group_not_split_when_it_fits():
    frame = pd.DataFrame([
        {"N°": i + 1, "UNIDADES": "A" if i < 20 else "B"}
        for i in range(30)
    ])
    pages = _paginate(frame)
    assert len(pages) == 2
    assert {row["UNIDADES"] for row in pages[0]} == {"A"}
    assert {row["UNIDADES"] for row in pages[1]} == {"B"}


def test_invalid_excel_file_raises_clear_error():
    invalid_bytes = BytesIO(b"esto no es un archivo excel")
    try:
        read_and_clean_excel(invalid_bytes)
    except InputFormatError as error:
        assert "No se pudo leer" in str(error)
    else:
        raise AssertionError("Se esperaba un InputFormatError")
