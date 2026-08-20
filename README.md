# Automatización Mundial

Aplicación de escritorio para automatizar procesos de Mundial de Seguros. La versión actual es **0.6.2** y, por ahora, implementa un único workflow: **Certificados ICBF**.

## Funcionalidades actuales

- Lectura y normalización de archivos Excel.
- Filtrado de novedades de ingreso.
- Revisión de registros, selección mediante `INCLUIR` y filtros de anomalías.
- Detección de documentos duplicados y campos obligatorios faltantes.
- Identificación y autorización manual de documentos no estándar.
- Edición controlada de `DOCUMENTO`, `PRIMER APELLIDO`, `SEGUNDO APELLIDO` y `UNIDADES`.
- Generación de PDF general y ZIP con un PDF por unidad.
- Reportes Excel de duplicados y campos faltantes.
- Texto sugerido para correo.

## Flujo general

```text
Seleccionar Excel → Procesar → Revisar registros → Corregir / excluir / autorizar → Generar PDF o ZIP
```

Consulte [las reglas de negocio vigentes](docs/business_rules.md) antes de preparar un archivo o interpretar una validación.

## Requisitos

- Para desarrollo: Python 3.11 o superior y las dependencias de `requirements.txt` y `requirements-dev.txt`.
- La distribución objetivo es Windows.
- El usuario empresarial final usa el ejecutable ONEDIR; no necesita instalar Python cuando recibe la carpeta completa de distribución.

## Ejecución de desarrollo

```powershell
python -m pytest -q
python main.py
```

## Arquitectura breve

- `app/`: ventana principal, registro de workflows, logging y operaciones de archivo compartidas.
- `config/`: configuración y recursos corporativos.
- `workflows/certificados_icbf/`: interfaz, modelos, servicio y lógica de Certificados ICBF.
- `tests/`: pruebas automatizadas.

## Documentación relacionada

- [Reglas de negocio vigentes](docs/business_rules.md)
- [Guía de usuario](docs/user_guide.md)
- [Protocolo de pruebas de aceptación](docs/acceptance_testing.md)
- [Build y distribución en Windows](docs/build_windows.md)
- [Cómo agregar workflows](docs/adding_workflows.md)
- [Auditoría histórica de migración](docs/migration_audit.md)
- [Historial de cambios](CHANGELOG.md)
