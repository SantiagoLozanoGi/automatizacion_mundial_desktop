# Changelog

Todos los cambios relevantes de la aplicación se documentarán en este archivo.

## [0.4.0] - 2026-08-14

### Cambiado

- Logo de certificados ubicado en la esquina superior izquierda de todas las páginas.
- PDF general configurado para una capacidad objetivo de hasta 70 registros por página.
- Paginación conserva unidades completas cuando caben y divide solo unidades mayores a la capacidad.
- Área de revisión y generación reorganizada en pestañas para priorizar la tabla de registros.
- Tabla y panel de detalle usan distribución flexible y crecen con la ventana.
- Pantalla de inicio adaptada a resoluciones estándar mediante un título responsive.

### Corregido

- Selección `INCLUIR` reversible y estable en la vista `Todos`, sin saltos por ordenamiento automático.
- Reportes de anomalías conservan la evidencia original independientemente de `INCLUIR`.
- Readiness y certificados continúan considerando únicamente los registros incluidos.
- Scrollbars vertical y horizontal con contraste y tamaño explícitos para el tema claro.

### Robustez y experiencia

- Logging centralizado y rotativo fuera del repositorio, con protección de datos personales.
- Manejo diferenciado de errores esperados e inesperados y captura global de excepciones.
- Escritura atómica para evitar archivos parciales y mensajes recuperables de guardado.
- Progreso indeterminado, prevención de tareas duplicadas y cierre seguro durante workers.
- Barra de estado conectada al flujo de procesamiento y generación.
- Últimas carpetas de apertura/guardado recordadas durante la sesión.
- Opción de abrir la carpeta de salida después de guardar correctamente.

## [0.3.0] - 2026-08-13

### Añadido

- Generación y guardado de PDF general mediante la aplicación.
- Generación asíncrona de ZIP con PDFs por unidad.
- Reportes Excel de duplicados y campos obligatorios faltantes cuando aplican.
- Texto sugerido para correo con actualización y copia al portapapeles.
- Nombres sugeridos centralizados y escritura reutilizable de salidas en disco.
- Estados de generación, prevención de ejecuciones dobles y manejo recuperable de errores.

### Corregido

- Asociación de campos faltantes con la fila correcta mediante `_FILA_ORIGEN`.

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
