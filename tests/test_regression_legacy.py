from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
import zipfile

import pandas as pd

from pypdf import PdfReader

from workflows.certificados_icbf.legacy.certificate_processor import (
    BODY_FONT_SIZE,
    BODY_MIN_FONT_SIZE,
    InputFormatError,
    _paginate,
    _paginate_by_height,
    final_records,
    format_date,
    generate_pdf,
    generate_pdf_zip_by_unit,
    normalize_unit_key,
    read_and_clean_excel,
    validate_records,
    validation_summary,
)


def test_height_pagination_mixes_units_and_preserves_order() -> None:
    frame = pd.DataFrame(
        {"UNIDADES": ["A"] * 21 + ["B"] * 4, "ORDEN": list(range(25))}
    )
    pages = _paginate_by_height(frame, [10.0] * len(frame), available_height=250.0)

    assert pages == [list(range(25))]


def test_height_pagination_starts_a_new_page_only_when_next_row_does_not_fit() -> None:
    frame = pd.DataFrame({"UNIDADES": ["A", "B", "B"], "ORDEN": [0, 1, 2]})
    pages = _paginate_by_height(frame, [10.0, 15.0, 10.0], available_height=25.0)

    assert pages == [[0, 1], [2]]
    assert BODY_FONT_SIZE == 6.8
    assert BODY_MIN_FONT_SIZE == 6.2


def test_format_date_converts_excel_serials() -> None:
    assert format_date(46213) == "10/07/2026"
    assert format_date(46221) == "18/07/2026"


def test_format_date_preserves_supported_date_inputs() -> None:
    assert format_date("10/07/2026") == "10/07/2026"
    assert format_date("10-07-2026") == "10/07/2026"
    assert format_date(datetime(2026, 7, 10)) == "10/07/2026"
    assert format_date(pd.Timestamp("2026-07-18")) == "18/07/2026"


def test_format_date_preserves_missing_and_impossible_values() -> None:
    assert format_date(None) == ""
    assert format_date("") == ""
    assert format_date("NA") == "NA"
    assert format_date(0) == "0"
    assert format_date(-5) == "-5"
    assert format_date(999_999_999) == "999999999"


def test_excel_serial_date_reaches_dataframe_pdf_and_zip_normalized() -> None:
    source = build_source([
        ["Ana", None, "Díaz", None, "123", 46213, "Bogotá", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)

    assert records.loc[0, "FECHA DE NACIMIENTO"] == "10/07/2026"
    pdf_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(generate_pdf(records))).pages
    )
    with zipfile.ZipFile(BytesIO(generate_pdf_zip_by_unit(records))) as archive:
        zipped_pdf = archive.read(archive.namelist()[0])
    zip_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(zipped_pdf)).pages
    )

    assert "10/07/2026" in pdf_text
    assert "10/07/2026" in zip_text


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

    records.loc[1, "DOCUMENTO"] = "0000000101"
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


def test_row_pagination_allows_units_to_share_a_page():
    frame = pd.DataFrame([
        {"N°": i + 1, "UNIDADES": "A" if i < 20 else "B"}
        for i in range(30)
    ])
    pages = _paginate(frame)
    assert [len(page) for page in pages] == [25, 5]
    assert {row["UNIDADES"] for row in pages[0]} == {"A", "B"}


def test_row_pagination_uses_remaining_capacity_after_a_unit_change():
    frame = pd.DataFrame([
        {"N°": index + 1, "UNIDADES": "A" if index < 55 else "B"}
        for index in range(75)
    ])

    pages = _paginate(frame, rows_per_page=70)

    assert [len(page) for page in pages] == [70, 5]
    assert {row["UNIDADES"] for row in pages[0]} == {"A", "B"}


def test_pagination_splits_only_unit_larger_than_capacity():
    frame = pd.DataFrame([
        {"N°": index + 1, "UNIDADES": "UNIDAD GRANDE"}
        for index in range(85)
    ])

    pages = _paginate(frame, rows_per_page=70)

    assert [len(page) for page in pages] == [70, 15]
    assert all({row["UNIDADES"] for row in page} == {"UNIDAD GRANDE"} for page in pages)


def test_normalize_unit_key_equates_only_separator_space_and_case_variants():
    variants = [
        "123_UNIDAD_PRUEBA",
        "123 - UNIDAD PRUEBA",
        "123-UNIDAD PRUEBA",
        " 123_UNIDAD  prueba ",
    ]
    assert {normalize_unit_key(value) for value in variants} == {"123 UNIDAD PRUEBA"}
    assert normalize_unit_key("124_UNIDAD_PRUEBA") == "124 UNIDAD PRUEBA"
    assert normalize_unit_key("124_UNIDAD_PRUEBA") != normalize_unit_key("123_UNIDAD_PRUEBA")


def test_unit_variants_share_pdf_zip_and_summary_but_keep_first_visible_name():
    source = build_source([
        ["Ana", None, "PÃ©rez", None, "123", "01/01/2010", "123_UNIDAD_PRUEBA", "INGRESO"],
        ["Luis", None, "GÃ³mez", None, "456", "02/02/2011", "123 - Unidad Prueba", "INGRESO"],
        ["Eva", None, "Rojas", None, "789", "03/03/2012", "456_OTRA UNIDAD", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)

    assert validation_summary(records)["unidades"] == 2
    ordered = final_records(records)
    assert ordered.loc[0, "UNIDADES"] == "123_UNIDAD_PRUEBA"

    zip_bytes = generate_pdf_zip_by_unit(records, generated_on=date(2026, 8, 14))
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        names = archive.namelist()
        unit_pdf = archive.read("CERTIFICADOS_123_UNIDAD_PRUEBA_14-08-2026.pdf")

    assert len(names) == 2
    assert "CERTIFICADOS_123_UNIDAD_PRUEBA_14-08-2026.pdf" in names
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(unit_pdf)).pages)
    assert "Ana" in pdf_text
    assert "Luis" in pdf_text


def test_invalid_excel_file_raises_clear_error():
    invalid_bytes = BytesIO(b"esto no es un archivo excel")
    try:
        read_and_clean_excel(invalid_bytes)
    except InputFormatError as error:
        assert "No se pudo leer" in str(error)
    else:
        raise AssertionError("Se esperaba un InputFormatError")
