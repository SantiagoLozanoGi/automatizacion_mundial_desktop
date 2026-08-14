# Automatización Mundial

Proyecto nuevo de escritorio para migrar la lógica funcional del prototipo Streamlit sin alterar su comportamiento original.

## Estructura

- app/: aplicación PySide6
- workflows/certificados_icbf/legacy/: lógica heredada copiada fielmente
- workflows/certificados_icbf/service.py: capa de servicio
- tests/: pruebas de regresión
- assets/: recursos de la UI
- config/: configuración

## Propósito

Mantener intacto el prototipo original bajo `automatizacion_certificados/` y migrar únicamente la lógica funcional heredada a una nueva base modular.

## Reglas de migración

- conservar algoritmos y nombres originales;
- no reescribir reglas de negocio;
- documentar incompatibilidades técnicas reales antes de cambiar comportamiento;
- verificar regresión antes de introducir la interfaz.
