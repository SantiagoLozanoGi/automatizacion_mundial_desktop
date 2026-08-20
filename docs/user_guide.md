# Guía de usuario: Certificados ICBF

## 1. Abrir la aplicación

Abra `AutomatizacionMundial.exe` desde la carpeta de distribución recibida. No mueva el ejecutable fuera de esa carpeta.

## 2. Entrar a Certificados ICBF

En el menú lateral, seleccione **Certificados ICBF**.

## 3. Seleccionar Excel

Seleccione **Seleccionar Excel**, busque el archivo y luego pulse **Procesar archivo**. Se aceptan archivos `.xlsx`, `.xlsm` y `.xls`.

## 4. Procesar

Espere a que finalice el procesamiento. La aplicación mostrará los registros procesables y el resumen de validación.

## 5. Interpretar el resumen

El resumen informa registros recibidos, procesables, seleccionados, no seleccionados, duplicados, documentos no estándar, campos faltantes y válidos seleccionados. Solo los registros incluidos determinan si puede generar salidas.

## 6. Revisar registros

Use el selector **Mostrar** para ver todos los registros o solo una categoría. Seleccione una fila para consultar sus mensajes. Puede alternar la casilla `INCLUIR` para decidir qué registros se incorporan a las salidas.

> Captura pendiente: pantalla de revisión.

## 7. Excluir o incluir

Desmarque `INCLUIR` para excluir una fila temporalmente. Puede volver a marcarla después; la información y las correcciones realizadas se conservan.

## 8. Editar campos

Haga doble clic en una celda para editar únicamente `DOCUMENTO`, `PRIMER APELLIDO`, `SEGUNDO APELLIDO` y `UNIDADES`. Después de editar, la validación se actualiza.

## 9. Autorizar un documento no estándar

Seleccione la fila y use **Autorizar documento no estándar**. Confirme solo después de revisar el dato. La autorización se puede revocar. Si edita el documento después de autorizarlo, deberá autorizarlo otra vez si sigue sin tener diez dígitos.

## 10. Generar PDF general

Cuando el estado indique que el archivo está listo, pulse **Generar PDF** y elija dónde guardarlo. El PDF puede contener registros sin unidad.

## 11. Generar ZIP

Pulse **Generar ZIP por unidad** cuando esté habilitado. Cada registro incluido debe tener unidad; de lo contrario, complete ese campo o excluya el registro antes de generar el ZIP.

## 12. Generar reportes

Si existen anomalías, puede generar el reporte Excel de **Duplicados** o de **Campos faltantes**. Estos reportes sirven para revisión y no corrigen los registros.

## 13. Copiar texto de correo

En la sección de generación encontrará un texto sugerido. Actualícelo tras cambios de selección si es necesario y use **Copiar** para llevarlo al portapapeles.

## Mensajes comunes

| Mensaje | Qué hacer |
| --- | --- |
| Documento duplicado | Corrija uno de los documentos o excluya la fila que no debe salir. |
| Documento no estándar | Corrija el documento o autorícelo explícitamente tras revisarlo. |
| Campos obligatorios faltantes | Complete nombre, documento, fecha y al menos un apellido, o excluya la fila. |
| ZIP bloqueado por unidades faltantes | Complete `UNIDADES` en todos los registros incluidos o excluya los que no correspondan. |
| Ningún registro seleccionado | Marque al menos una casilla `INCLUIR`. |

Para el detalle de reglas consulte [Reglas de negocio vigentes](business_rules.md).
