from __future__ import annotations

from io import BytesIO
import zipfile

import pandas as pd
from pypdf import PdfReader
from reportlab.pdfbase import pdfmetrics

from workflows.certificados_icbf.legacy.certificate_processor import (
    BODY_FONT_SIZE,
    InputFormatError,
    UNIT_MIN_FONT_SIZE,
    _register_font,
    _unit_text_layout,
    _paginate,
    final_records,
    generate_pdf,
    generate_pdf_zip_by_unit,
    read_and_clean_excel,
    validate_records,
)


def build_source(rows):
    """Build a temporary Excel source from test rows."""
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
    """Verify validation flow and standard PDF/ZIP generation."""
    source = build_source([
        ["Ana", None, "Díaz", None, "100", "01/01/2010", "Bogotá", "INGRESO"],
        ["Luis", "NA", "Pérez", "NA", "100", "02/02/2011", "Bogotá", "IN"],
        ["Eva", None, "Rojas", None, None, "03/03/2012", "Cali", "INGRESO"],
        ["No", "Pasa", "Esta", "Fila", "999", "04/04/2013", "Cali", "EX"],
    ])
    records, stats = read_and_clean_excel(source)
    assert stats == {"recibidos": 4, "ingresos": 3, "excluidos": 1}
    assert set(records["SEGUNDO NOMBRE"]) == {""}
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
    """Ensure missing required fields are reported correctly."""
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
    assert missing_row["SEGUNDO NOMBRE"] == ""
    assert missing_row["SEGUNDO APELLIDO"] == ""
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
    """Allow records that have second surname when first surname is absent."""
    source = build_source([
        ["Ana", None, None, "Gómez", "123", "01/01/2010", "Bogotá", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)
    validation = validate_records(records)

    assert len(validation["missing_report"]) == 0
    assert validation["blocking"] is False


def test_invalid_document_blocks_pdf():
    """Confirm invalid document values block PDF generation."""
    source = build_source([
        ["Ana", None, "Díaz", None, "ABC123", "01/01/2010", "Bogotá", "INGRESO"],
        ["Eva", None, "Rojas", None, "12345678901", "03/03/2012", "Cali", "INGRESO"],
    ])
    records, _ = read_and_clean_excel(source)
    validation = validate_records(records)
    assert validation["blocking"] is True
    assert len(validation["invalid_document"]) == 2


def test_row_pagination_allows_units_to_share_a_page():
    """Validate pagination keeps unit groups together when possible."""
    frame = pd.DataFrame([
        {"N°": i + 1, "UNIDADES": "A" if i < 20 else "B"}
        for i in range(30)
    ])
    pages = _paginate(frame)
    assert [len(page) for page in pages] == [25, 5]
    assert {row["UNIDADES"] for row in pages[0]} == {"A", "B"}


def test_generate_pdf_with_seventy_rows_same_unit():
    """Check that 70 rows of the same unit fit on one PDF page."""
    rows = [
        ["Ana", None, "Díaz", None, str(100 + i), "01/01/2010", "Bogotá", "INGRESO"]
        for i in range(70)
    ]
    source = build_source(rows)
    records, _ = read_and_clean_excel(source)
    records["DOCUMENTO"] = records["DOCUMENTO"].map(lambda value: str(value).zfill(10))
    pdf = generate_pdf(records, rows_per_page=70)
    assert pdf.startswith(b"%PDF")
    pages = PdfReader(BytesIO(pdf)).pages
    assert len(pages) == 1


def test_long_unit_names_wrap_in_general_pdf_and_unit_zip():
    """Unit names remain complete when the PDF renderer wraps them."""
    units = [
        "UNIDAD PRUEBA",
        "CENTRO INFANTIL UNIDAD PRUEBA",
        "CENTRO DE DESARROLLO INFANTIL UNIDAD DE PRUEBA EXTENSA",
    ]
    regular_font, _ = _register_font()
    expected_lines = [1, 1, 2]
    for unit, line_count in zip(units, expected_lines):
        font_size, lines = _unit_text_layout(unit, 104, regular_font, BODY_FONT_SIZE)
        assert font_size >= UNIT_MIN_FONT_SIZE
        assert len(lines) == line_count
        assert " ".join(lines) == unit

    source = build_source([
        ["Ana", None, "PÃ©rez", None, str(100 + index), "01/01/2010", unit, "INGRESO"]
        for index, unit in enumerate(units)
    ])
    records, _ = read_and_clean_excel(source)

    pdf = generate_pdf(records)
    assert pdf.startswith(b"%PDF")
    general_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    for word in units[-1].split():
        assert word in general_text

    zip_bytes = generate_pdf_zip_by_unit(records)
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        unit_pdfs = [archive.read(name) for name in archive.namelist()]
    assert len(unit_pdfs) == len(units)
    zip_text = "\n".join(
        page.extract_text() or ""
        for unit_pdf in unit_pdfs
        for page in PdfReader(BytesIO(unit_pdf)).pages
    )
    for unit in units:
        for word in unit.split():
            assert word in zip_text


def test_unit_layout_reduces_before_wrapping_and_respects_minimum_font() -> None:
    regular_font, _ = _register_font()
    value = "FUNDADORES RIOBLANCO"
    base_width = pdfmetrics.stringWidth(value, regular_font, BODY_FONT_SIZE)
    minimum_width = pdfmetrics.stringWidth(value, regular_font, UNIT_MIN_FONT_SIZE)
    width = (base_width + minimum_width) / 2

    size, lines = _unit_text_layout(value, width, regular_font, BODY_FONT_SIZE)

    assert len(lines) == 1
    assert UNIT_MIN_FONT_SIZE <= size < BODY_FONT_SIZE


def test_very_long_unit_uses_at_most_two_lines_at_readable_size() -> None:
    regular_font, _ = _register_font()
    value = "CENTRO DE DESARROLLO INFANTIL PARA LA PRIMERA INFANCIA RIOBLANCO"

    size, lines = _unit_text_layout(value, 130, regular_font, BODY_FONT_SIZE)

    assert len(lines) <= 2
    assert size >= UNIT_MIN_FONT_SIZE


def test_invalid_excel_file_raises_clear_error():
    """Ensure a malformed Excel file raises an InputFormatError."""
    invalid_bytes = BytesIO(b"esto no es un archivo excel")
    try:
        read_and_clean_excel(invalid_bytes)
    except InputFormatError as error:
        assert "No se pudo leer" in str(error)
    else:
        raise AssertionError("Se esperaba un InputFormatError")


if __name__ == "__main__":
    test_validation_and_pdf()
    test_reports_only_ingresos_and_required_fields()
    test_invalid_document_blocks_pdf()
    test_city_group_not_split_when_it_fits()
    print("Pruebas correctas")
