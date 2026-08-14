from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Any

import pandas as pd

from app.logging_config import get_logger
from config.resources import CORPORATE_LOGO_PATH
from workflows.certificados_icbf.legacy.certificate_processor import (
    build_email_text,
    dataframe_to_excel_bytes,
    final_records,
    generate_pdf,
    generate_pdf_zip_by_unit,
    is_missing,
    normalize_edited_records,
    read_and_clean_excel,
    validate_records,
    validation_summary,
)


EDITABLE_FIELDS = frozenset({"DOCUMENTO", "PRIMER APELLIDO", "SEGUNDO APELLIDO"})
_LOG_FIELD_NAMES = {
    "DOCUMENTO": "document",
    "PRIMER APELLIDO": "first_surname",
    "SEGUNDO APELLIDO": "second_surname",
}
logger = get_logger("certificados_icbf")


class ReviewSession:
    """Cache validation metadata while only the INCLUIR selection changes."""

    def __init__(self, records: pd.DataFrame) -> None:
        self._records = records.copy(deep=True).reset_index(drop=True)
        self._build_cache()

    @property
    def records(self) -> pd.DataFrame:
        return self._records.copy(deep=True)

    def _build_cache(self) -> None:
        validation_input = self._records.copy(deep=True)
        validation_input["INCLUIR"] = True
        validation = validate_records(validation_input)
        self._duplicates_report = validation["duplicates"].copy(deep=True)
        self._missing_report = validation["missing_report"].copy(deep=True)
        self._invalid_indexes = set(validation["invalid_document"].index)
        self._missing_document_indexes = set(validation["missing_document"].index)
        index_by_source_row = {
            source_row: index
            for index, source_row in self._records["_FILA_ORIGEN"].items()
        }
        self._missing_by_index = {
            index_by_source_row[row["_FILA_ORIGEN"]]: str(
                row["CAMPOS OBLIGATORIOS FALTANTES"]
            )
            for _, row in validation["missing_report"].iterrows()
            if row["_FILA_ORIGEN"] in index_by_source_row
        }
        self._duplicate_groups = [
            set(group.index)
            for _, group in validation["duplicates"].groupby("DOCUMENTO", sort=False)
        ]
        self._duplicate_indexes = set().union(*self._duplicate_groups) if self._duplicate_groups else set()

    def revalidate(self, records: pd.DataFrame) -> dict[str, Any]:
        """Replace business data and rebuild the cache after a future field edit."""
        self._records = records.copy(deep=True).reset_index(drop=True)
        self._build_cache()
        return self.snapshot()

    def set_included(self, row: int, included: bool) -> dict[str, Any]:
        if not 0 <= row < len(self._records):
            raise IndexError("La fila seleccionada no existe.")
        self._records.iat[row, self._records.columns.get_loc("INCLUIR")] = bool(included)
        return self.snapshot()

    def report_frame(self, report_type: str) -> pd.DataFrame:
        reports = {
            "duplicates": self._duplicates_report,
            "missing": self._missing_report,
        }
        if report_type not in reports:
            raise ValueError(f"Tipo de reporte desconocido: {report_type}")
        return reports[report_type].copy(deep=True)

    def snapshot(self) -> dict[str, Any]:
        included_indexes = {
            index for index, value in self._records["INCLUIR"].items() if bool(value)
        }
        duplicate_indexes: set[int] = set()
        for group in self._duplicate_groups:
            selected_group = group & included_indexes
            if len(selected_group) > 1:
                duplicate_indexes.update(selected_group)
        invalid_indexes = self._invalid_indexes & included_indexes
        missing_indexes = set(self._missing_by_index) & included_indexes
        problem_indexes = duplicate_indexes | invalid_indexes | missing_indexes

        rows: dict[int, dict[str, Any]] = {}
        for index, row in self._records.iterrows():
            included = index in included_indexes
            anomalies: list[str] = []
            categories: set[str] = set()
            if index in self._duplicate_indexes:
                anomalies.append(f"Documento duplicado: {row['DOCUMENTO']}")
                categories.add("duplicates")
            if index in self._invalid_indexes:
                anomalies.append(f"Documento inválido: {row['DOCUMENTO']}")
                categories.add("invalid")
            if index in self._missing_by_index:
                anomalies.append(
                    f"Campos obligatorios faltantes: {self._missing_by_index[index]}"
                )
                categories.add("missing")
            if not included:
                status = "No incluido"
                categories.add("excluded")
            elif index in problem_indexes:
                status = "Requiere revisión"
            else:
                status = "Válido"
                categories.add("valid")
            categories.add("included" if included else "excluded")
            rows[index] = {"status": status, "anomalies": anomalies, "categories": categories}

        active = self._records.loc[sorted(included_indexes)].copy()
        units = active["UNIDADES"].map(lambda value: "NA" if is_missing(value) else value)
        selected = len(included_indexes)
        summary = {
            "registros_activos": selected,
            "registros_validos": selected - len(problem_indexes),
            "documentos_faltantes": len(self._missing_document_indexes & included_indexes),
            "documentos_invalidos": len(invalid_indexes),
            "filas_duplicadas": len(duplicate_indexes),
            "campos_informativos": len(missing_indexes),
            "unidades": units.nunique(dropna=False),
            "blocking": bool(problem_indexes),
            "total_procesado": len(self._records),
            "no_seleccionados": len(self._records) - selected,
            "reporte_duplicados": len(self._duplicates_report),
            "reporte_faltantes": len(self._missing_report),
        }
        ready = selected > 0 and not summary["blocking"]
        return {
            "rows": rows,
            "summary": summary,
            "ready": ready,
            "status": "Listo para generación" if ready else "Requiere revisión",
            "blocking_reason": "" if ready else CertificadosIcbfService._blocking_reason(summary, selected),
        }


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

    def generate_pdf(self, records, rows_per_page=70, logo_path: str | Path | None = None):
        self._ensure_ready(records)
        logo = Path(logo_path) if logo_path else self.logo_path
        if not logo.exists():
            return generate_pdf(records, rows_per_page=rows_per_page)
        return generate_pdf(records, rows_per_page=rows_per_page, logo_path=str(logo))

    def generate_pdf_zip_by_unit(self, records, rows_per_page=25, logo_path: str | Path | None = None):
        self._ensure_ready(records)
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

    def set_included(self, records: pd.DataFrame, row: int, included: bool) -> pd.DataFrame:
        """Return a working copy with the requested INCLUIR value changed."""
        if "INCLUIR" not in records.columns:
            raise KeyError("El conjunto de registros no contiene la columna INCLUIR.")
        if not 0 <= row < len(records):
            raise IndexError("La fila seleccionada no existe.")
        updated = records.copy(deep=True)
        updated.iat[row, updated.columns.get_loc("INCLUIR")] = bool(included)
        return updated

    def update_editable_field(
        self, records: pd.DataFrame, row: int, field: str, value: object
    ) -> pd.DataFrame:
        """Update and normalize one authorized field in a working copy."""
        if field not in EDITABLE_FIELDS:
            raise ValueError(f"El campo no admite edición manual: {field}")
        if field not in records.columns:
            raise KeyError(f"El conjunto de registros no contiene la columna {field}.")
        if not 0 <= row < len(records):
            raise IndexError("La fila seleccionada no existe.")
        updated = records.copy(deep=True).reset_index(drop=True)
        source_row = updated.iloc[row]["_FILA_ORIGEN"]
        updated.iat[row, updated.columns.get_loc(field)] = value
        normalized = normalize_edited_records(updated)
        logger.info(
            "workflow=certificados_icbf action=manual_edit field=%s source_row=%s",
            _LOG_FIELD_NAMES[field],
            source_row,
        )
        return normalized

    def review_records(self, records: pd.DataFrame) -> dict[str, Any]:
        """Prepare row-level validation information for the review interface."""
        return self.create_review_session(records).snapshot()

    def create_review_session(self, records: pd.DataFrame) -> ReviewSession:
        return ReviewSession(records)

    def output_availability(self, records: pd.DataFrame) -> dict[str, Any]:
        validation = validate_records(records)
        report_session = self.create_review_session(records)
        selected = len(validation["active"])
        ready = selected > 0 and not bool(validation["blocking"])
        return {
            "ready": ready,
            "selected": selected,
            "duplicates": len(report_session.report_frame("duplicates")),
            "missing": len(report_session.report_frame("missing")),
            "email_text": build_email_text(records),
        }

    def generate_duplicates_report(self, records: pd.DataFrame | ReviewSession) -> bytes:
        session = records if isinstance(records, ReviewSession) else self.create_review_session(records)
        duplicates = session.report_frame("duplicates")
        if duplicates.empty:
            raise ValueError("No hay documentos duplicados en el archivo procesado para reportar.")
        return dataframe_to_excel_bytes({"Duplicados": duplicates})

    def generate_missing_fields_report(self, records: pd.DataFrame | ReviewSession) -> bytes:
        session = records if isinstance(records, ReviewSession) else self.create_review_session(records)
        missing = session.report_frame("missing")
        if missing.empty:
            raise ValueError("No hay campos obligatorios faltantes en el archivo procesado para reportar.")
        return dataframe_to_excel_bytes({"Campos faltantes": missing})

    def suggested_filename(
        self,
        source_path: str | Path,
        output_type: str,
        generated_on: date | None = None,
    ) -> str:
        source_name = Path(source_path).stem
        safe_base = re.sub(r'[<>:"/\\|?*]+', "-", source_name).strip(" .-") or "ARCHIVO"
        stamp = (generated_on or date.today()).strftime("%Y%m%d")
        patterns = {
            "pdf": f"CERTIFICADO-{safe_base}-{stamp}.pdf",
            "zip": f"CERTIFICADO-{safe_base}-{stamp}.zip",
            "duplicates": f"REPORTE-DUPLICADOS-{safe_base}-{stamp}.xlsx",
            "missing": f"REPORTE-CAMPOS-FALTANTES-{safe_base}-{stamp}.xlsx",
        }
        if output_type not in patterns:
            raise ValueError(f"Tipo de salida desconocido: {output_type}")
        return patterns[output_type]

    def _ensure_ready(self, records: pd.DataFrame) -> None:
        availability = self.output_availability(records)
        if not availability["ready"]:
            raise ValueError("Los registros seleccionados todavía requieren revisión.")

    @staticmethod
    def _blocking_reason(summary: dict[str, Any], selected: int) -> str:
        if selected == 0:
            return "Selecciona al menos un registro mediante INCLUIR."
        reasons = []
        if summary["filas_duplicadas"]:
            reasons.append("documentos duplicados")
        if summary["documentos_invalidos"]:
            reasons.append("documentos inválidos")
        if summary["campos_informativos"]:
            reasons.append("campos obligatorios faltantes")
        return "Debes revisar: " + ", ".join(reasons) + "."


service = CertificadosIcbfService()


def run_service_demo() -> None:
    print("Servicio listo para la migración controlada de certificados ICBF.")
    print("Se conserva la lógica heredada en workflows/certificados_icbf/legacy/.")
