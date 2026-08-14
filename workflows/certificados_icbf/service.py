from __future__ import annotations

from pathlib import Path
from typing import Any

from config.resources import CORPORATE_LOGO_PATH
from workflows.certificados_icbf.legacy.certificate_processor import (
    build_email_text,
    dataframe_to_excel_bytes,
    final_records,
    generate_pdf,
    generate_pdf_zip_by_unit,
    read_and_clean_excel,
    validate_records,
    validation_summary,
)


class CertificadosIcbfService:
    """Capa de servicio que encapsula la lógica heredada sin reescribirla."""

    def __init__(self) -> None:
        self.logo_path = CORPORATE_LOGO_PATH

    def read_and_clean_excel(self, file_or_buffer: Any):
        return read_and_clean_excel(file_or_buffer)

    def validate_records(self, records):
        return validate_records(records)

    def final_records(self, records):
        return final_records(records)

    def generate_pdf(self, records, rows_per_page=25, logo_path: str | Path | None = None):
        logo = Path(logo_path) if logo_path else self.logo_path
        if not logo.exists():
            return generate_pdf(records, rows_per_page=rows_per_page)
        return generate_pdf(records, rows_per_page=rows_per_page, logo_path=str(logo))

    def generate_pdf_zip_by_unit(self, records, rows_per_page=25, logo_path: str | Path | None = None):
        logo = Path(logo_path) if logo_path else self.logo_path
        if not logo.exists():
            return generate_pdf_zip_by_unit(records, rows_per_page=rows_per_page)
        return generate_pdf_zip_by_unit(records, rows_per_page=rows_per_page, logo_path=str(logo))

    def build_email_text(self, records):
        return build_email_text(records)

    def dataframe_to_excel_bytes(self, sheets):
        return dataframe_to_excel_bytes(sheets)

    def validation_summary(self, records):
        return validation_summary(records)


service = CertificadosIcbfService()


def run_service_demo() -> None:
    print("Servicio listo para la migración controlada de certificados ICBF.")
    print("Se conserva la lógica heredada en workflows/certificados_icbf/legacy/.")
