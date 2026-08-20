# Auditoría de migración: Streamlit a PySide6

> **Nota histórica:** este documento describe la migración inicial. Las reglas y comportamientos funcionales pueden haber evolucionado después de esa etapa. La fuente de verdad funcional vigente es [Reglas de negocio: Certificados ICBF](business_rules.md).

## 1. Proyecto original analizado

El prototipo original queda intacto en `automatizacion_certificados/` y no se modifica durante esta migración.

### Archivos principales

- `app.py`: flujo principal del prototipo, manejo de UI y generación de PDFs.
- `certificate_processor.py`: lógica de negocio y generación de archivos.
- `test_processor.py`: pruebas funcionales de regresión de la lógica.

### Funciones de negocio

- `read_and_clean_excel()`: lectura de Excel y limpieza.
- `validate_records()`: validación de documentos, duplicados y campos obligatorios.
- `final_records()`: ordenamiento final para impresión y PDF.
- `generate_pdf()`: creación de PDF único.
- `generate_pdf_zip_by_unit()`: ZIP de PDFs por unidad.
- `dataframe_to_excel_bytes()`: exportación a Excel.

### Funciones de interfaz

- UI de Streamlit en `app.py` para upload, edición, validación y descarga.
- render de reportes y alertas por validación.
- acciones de usuario para autorizar PDF.

### Funciones mezcladas

- `app.py` mezcla lógica de flujo con lógica de presentación y control de sesión.
- `build_email_text()` y `validation_summary()` están en el módulo de negocio pero apuntan al flujo de UI.

### Dependencias relevantes

- `pandas`
- `openpyxl`
- `reportlab`
- `pypdf`
- `streamlit`
- `pytest`

### Entradas y salidas

Entradas:

- Excel con columnas de nombre, documento, fecha, unidad y tipo de novedad.

Salidas:

- DataFrame limpio.
- reportes de duplicados y campos faltantes.
- PDF o ZIP por unidad.
- archivos de descarga Excel.

### Rutas, temporales y artefactos

- uso de `BytesIO` para archivos en memoria;
- sin rutas persistentes por defecto;
- generación de PDF y ZIP en memoria, sin almacenamiento local en el flujo de negocio;
- nombres de descarga con patrón `CERTIFICADO-{base}-{fecha}.pdf` o `.zip`.

### Validaciones clave

- columnas requeridas y alias de encabezados;
- campo `TIPO DE NOVEDAD` filtrando `IN`/`INGRESO`;
- documentos con normalización a 10 dígitos;
- validación de duplicados por documento;
- obligatorios: nombre, documento, fecha y unidad;
- segundo nombre/apellido no obligatorio; basta con primer apellido o segundo apellido.

## 2. Migración aplicada

Se crea una nueva estructura modular para mantener la lógica copiada sin reescribirla.

- `workflows/certificados_icbf/legacy/...`: lógica heredada intacta.
- `workflows/certificados_icbf/service.py`: capa intermedia.
- `workflows/certificados_icbf/view.py`: vista PySide6 mínima, sin reglas de negocio.
- `tests/test_regression_legacy.py`: pruebas heredadas adaptadas al nuevo paquete.

## 3. Regla de protección

Se respetan los algoritmos del prototipo original y solo se aplican adaptaciones técnicas necesarias de importación y empaquetado.
