from datetime import date
from io import BytesIO
import zipfile

import pandas as pd
import pytest
from pypdf import PdfReader

from workflows.certificados_icbf.models import RecordsTableModel
from workflows.certificados_icbf.service import CertificadosIcbfService
from workflows.certificados_icbf.legacy.certificate_processor import validate_records


def records_with(document: str) -> pd.DataFrame:
    return pd.DataFrame([{
        "INCLUIR": True,
        "PRIMER NOMBRE": "PERSONA",
        "SEGUNDO NOMBRE": "NA",
        "PRIMER APELLIDO": "PRUEBA",
        "SEGUNDO APELLIDO": "NA",
        "DOCUMENTO": document,
        "FECHA DE NACIMIENTO": "01/01/2000",
        "UNIDADES": "UNIDAD PRUEBA",
        "_FILA_ORIGEN": 25,
    }])


def test_excel_document_with_dots_is_cleaned_before_classification() -> None:
    source = BytesIO()
    pd.DataFrame([{
        "Primer Nombre": "PERSONA",
        "Segundo Nombre": "NA",
        "Primer Apellido": "PRUEBA",
        "Segundo Apellido": "NA",
        "Número de Identificación": "1.234.567.890",
        "Fecha de Nacimiento": "01/01/2000",
        "UNIDADES": "UNIDAD PRUEBA",
        "Tipo de Novedad": "INGRESO",
    }]).to_excel(source, index=False)
    source.seek(0)

    records, _ = CertificadosIcbfService().read_and_clean_excel(source)

    assert records.loc[0, "DOCUMENTO"] == "1234567890"
    assert validate_records(records)["blocking"] is False


@pytest.mark.parametrize("document", ["1234567", "123456789012", "PAS12345"])
def test_nonstandard_documents_are_literal_and_block_until_authorized(document: str) -> None:
    session = CertificadosIcbfService().create_review_session(records_with(document))

    assert session.records.loc[0, "DOCUMENTO"] == document
    assert session.snapshot()["ready"] is False
    assert "nonstandard" in session.snapshot()["rows"][0]["categories"]

    session.authorize_document_exception(0)

    assert session.records.loc[0, "DOCUMENTO"] == document
    assert session.snapshot()["ready"] is True
    assert session.snapshot()["rows"][0]["status"] == "Excepción documental autorizada"


def test_standard_document_is_automatic_and_cannot_be_exception() -> None:
    session = CertificadosIcbfService().create_review_session(records_with("1234567890"))
    assert session.snapshot()["ready"] is True
    with pytest.raises(ValueError, match="formato estándar"):
        session.authorize_document_exception(0)


def test_letters_zeroes_case_spaces_and_special_characters_are_preserved() -> None:
    service = CertificadosIcbfService()
    for document in ("AB001234", "ab001234", "AB 00-1234"):
        updated = service.update_editable_field(records_with("1234567890"), 0, "DOCUMENTO", document)
        assert updated.loc[0, "DOCUMENTO"] == document


def test_revocation_and_document_edit_invalidate_authorization() -> None:
    service = CertificadosIcbfService()
    model = RecordsTableModel(records_with("PAS12345"), service)
    model.authorize_document_exception(0)
    assert model.review["ready"] is True

    model.revoke_document_exception(0)
    assert model.review["ready"] is False
    model.authorize_document_exception(0)
    document_column = model._columns.index("DOCUMENTO")
    model.setData(model.index(0, document_column), "PAS12346")

    assert model.review_session.authorized_document_exceptions == frozenset()
    assert model.review["ready"] is False
    assert "nonstandard" in model.categories_for_row(0)


def test_edit_to_standard_needs_no_authorization() -> None:
    model = RecordsTableModel(records_with("PAS12345"))
    document_column = model._columns.index("DOCUMENTO")
    model.setData(model.index(0, document_column), "1234567890")
    assert model.review["ready"] is True
    assert "nonstandard" not in model.categories_for_row(0)


@pytest.mark.parametrize("document", ["", "NA", "N/A"])
def test_missing_document_cannot_be_authorized(document: str) -> None:
    session = CertificadosIcbfService().create_review_session(records_with(document))
    with pytest.raises(ValueError, match="faltante"):
        session.authorize_document_exception(0)


def test_authorized_alphanumeric_document_reaches_pdf_and_named_zip() -> None:
    service = CertificadosIcbfService()
    session = service.create_review_session(records_with("PAS12345"))
    session.authorize_document_exception(0)
    authorization = session.authorized_document_exceptions

    pdf = service.generate_pdf(session.records, authorized_document_exceptions=authorization)
    archive = service.generate_pdf_zip_by_unit(
        session.records,
        authorized_document_exceptions=authorization,
        generated_on=date(2026, 8, 14),
    )
    pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)
    with zipfile.ZipFile(BytesIO(archive)) as zipped:
        assert zipped.namelist() == ["CERTIFICADOS_UNIDAD_PRUEBA_14-08-2026.pdf"]
        unit_pdf = zipped.read(zipped.namelist()[0])
    unit_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(unit_pdf)).pages)

    assert "PAS12345" in pdf_text
    assert "PAS12345" in unit_text


@pytest.mark.parametrize(
    ("entered", "normalized", "ready"),
    [
        ("1.234.567.890", "1234567890", True),
        ("PAS.12345", "PAS12345", False),
        ("12.345", "12345", False),
    ],
)
def test_manual_document_edit_removes_only_dots(
    entered: str, normalized: str, ready: bool
) -> None:
    service = CertificadosIcbfService()
    updated = service.update_editable_field(
        records_with("1234567890"), 0, "DOCUMENTO", entered
    )
    session = service.create_review_session(updated)

    assert updated.loc[0, "DOCUMENTO"] == normalized
    assert session.snapshot()["ready"] is ready


def test_duplicate_detection_uses_document_without_dots() -> None:
    records = pd.concat(
        [records_with("1234567890"), records_with("1.234.567.890")],
        ignore_index=True,
    )
    records.loc[1, "_FILA_ORIGEN"] = 26

    validation = validate_records(records)

    assert validation["active"]["DOCUMENTO"].tolist() == ["1234567890", "1234567890"]
    assert len(validation["duplicates"]) == 2


def test_cleaned_document_is_used_in_pdf() -> None:
    service = CertificadosIcbfService()
    records = service.update_editable_field(
        records_with("0000000000"), 0, "DOCUMENTO", "1.234.567.890"
    )
    pdf = service.generate_pdf(records)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf)).pages)

    assert "1234567890" in text
    assert "1.234.567.890" not in text


def test_any_document_edit_revokes_authorization_even_if_clean_value_matches() -> None:
    service = CertificadosIcbfService()
    model = RecordsTableModel(records_with("PAS12345"), service)
    model.authorize_document_exception(0)
    document_column = model._columns.index("DOCUMENTO")

    model.setData(model.index(0, document_column), "PAS.12345")

    assert model.records.loc[0, "DOCUMENTO"] == "PAS12345"
    assert model.review_session.authorized_document_exceptions == frozenset()
    assert model.review["ready"] is False
