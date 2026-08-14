from __future__ import annotations

from typing import Any

from workflows.certificados_icbf.legacy.certificate_processor import (
    build_email_text,
    final_records,
    generate_pdf,
    generate_pdf_zip_by_unit,
    read_and_clean_excel,
    validate_records,
)


class CertificadosIcbfService:
    """Capa de servicio que encapsula la lógica heredada sin reescribirla."""

    def read_and_clean_excel(self, file_or_buffer: Any):
        return read_and_clean_excel(file_or_buffer)

    def validate_records(self, records):
        return validate_records(records)

    def final_records(self, records):
        return final_records(records)

    def generate_pdf(self, records, rows_per_page=25):
        return generate_pdf(records, rows_per_page=rows_per_page)

    def generate_pdf_zip_by_unit(self, records, rows_per_page=25):
        return generate_pdf_zip_by_unit(records, rows_per_page=rows_per_page)

    def build_email_text(self, records):
        return build_email_text(records)


service = CertificadosIcbfService()


def run_service_demo() -> None:
    print("Servicio listo para la migración controlada de certificados ICBF.")
    print("Se conserva la lógica heredada en workflows/certificados_icbf/legacy/.")
