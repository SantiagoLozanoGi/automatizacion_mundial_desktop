# Changelog

Todos los cambios relevantes de la aplicación se documentarán en este archivo.

## [0.2.0] - 2026-08-13

### Añadido

- Tabla de revisión basada en `QTableView` y un modelo de datos separado.
- Selección humana mediante checkboxes sobre la columna `INCLUIR` existente.
- Estados textuales y detalle por fila para duplicados, documentos inválidos y campos faltantes.
- Filtros visuales que no eliminan registros del DataFrame de trabajo.
- Resumen sincronizado y estado general listo para generación o requiere revisión.
- Botón conceptual de continuación, sin implementar salidas de v0.3.0.
- API de revisión centralizada en el servicio y pruebas de servicio/modelo.

### Corregido

- Contraste explícito para texto, fondos, encabezados y selección de la tabla en temas claros y oscuros.
- Caché de revisión para evitar validaciones completas repetidas al cambiar `INCLUIR`.
- Carga visual de la tabla sin escanear todas las celdas para calcular anchos automáticamente.

## [0.1.0] - 2026-08-13

### Añadido

- Arquitectura modular inicial para múltiples flujos de trabajo.
- Integración del flujo Certificados ICBF mediante una capa de servicio.
- Soporte de logo corporativo en todas las páginas de PDF.
- Pruebas del flujo mediante el servicio.
- Interfaz de inicio, selección de Excel, procesamiento asíncrono y resumen.
