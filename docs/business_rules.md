# Reglas de negocio vigentes: Certificados ICBF

Este documento describe el comportamiento funcional actual de la herramienta. Para el historial de cambios consulte [CHANGELOG.md](../CHANGELOG.md).

## Entrada Excel

La aplicación busca la fila de encabezados dentro de las primeras 20 filas. Para reconocerla requiere `PRIMER NOMBRE` y `NUMERO DE IDENTIFICACION` o `DOCUMENTO`.

### Columnas requeridas para procesar

| Campo interno | Encabezados reconocidos |
| --- | --- |
| `PRIMER NOMBRE` | `PRIMER NOMBRE` |
| `SEGUNDO NOMBRE` | `SEGUNDO NOMBRE` |
| `PRIMER APELLIDO` | `PRIMER APELLIDO` |
| `SEGUNDO APELLIDO` | `SEGUNDO APELLIDO` |
| `DOCUMENTO` | `NUMERO DE IDENTIFICACION`, `NUMERO DOCUMENTO`, `DOCUMENTO`, `NRO DOCUMENTO` |
| `FECHA DE NACIMIENTO` | `FECHA DE NACIMIENTO`, `FECHA NACIMIENTO` |

### Columnas opcionales

| Campo interno | Encabezados reconocidos | Comportamiento |
| --- | --- | --- |
| `UNIDADES` | `UNIDADES`, `UNIDAD` | Si falta, se crea vacío y puede completarse durante la revisión. |
| `TIPO DE NOVEDAD` | `TIPO DE NOVEDAD`, `NOVEDAD` | Si existe, controla el filtro de ingreso. Si falta, no se aplica ese filtro. |

Las filas completamente vacías se descartan. Las fechas se normalizan a `dd/mm/aaaa` cuando son reconocibles, incluidas fechas seriales de Excel.

## TIPO DE NOVEDAD

Cuando la columna está presente, solo se conservan estos valores de ingreso:

```text
IN
INGRESO
INGRES0
1NGRESO
```

La comparación normaliza mayúsculas/minúsculas, acentos y espacios. `INGRES0` usa cero final y `1NGRESO` usa uno inicial. No existe fuzzy matching general: cualquier otro valor se excluye.

## Documentos

- El formato estándar es exactamente diez dígitos.
- Al leer Excel, documentos numéricos de hasta diez dígitos se completan con ceros a la izquierda. Se eliminan puntos como separadores aprobados.
- En una edición manual también se eliminan puntos, pero no se aplica relleno adicional de ceros; letras, espacios, guiones y otros caracteres se conservan.
- Un documento no estándar no permite generar salidas hasta que una persona lo autorice explícitamente desde la revisión. Un documento faltante no puede autorizarse.
- La autorización se asocia a la fila de origen y al valor del documento. Editar el documento revoca la autorización, incluso si la normalización produce el mismo valor.
- Solo los documentos estándar participan en la detección de duplicados. Dos o más registros incluidos con el mismo documento estándar bloquean la generación.

## Campos obligatorios para el PDF general

En los registros incluidos deben existir `PRIMER NOMBRE`, `DOCUMENTO`, `FECHA DE NACIMIENTO` y al menos uno entre `PRIMER APELLIDO` o `SEGUNDO APELLIDO`. Los valores vacíos y marcadores como `NA`, `N/A`, `NONE`, `NAN` o `NULL` se consideran faltantes.

`SEGUNDO NOMBRE` y `SEGUNDO APELLIDO` pueden quedar como `NA`.

> `UNIDADES` **NO** es obligatoria para generar el PDF general.

## UNIDADES

- Es un campo editable durante la revisión.
- Puede estar vacío para el PDF general.
- Los registros incluidos sin unidad bloquean exclusivamente el ZIP por unidad; los excluidos sin unidad no lo bloquean.
- Para agrupar se normalizan acentos, mayúsculas, espacios y los separadores `_`/`-`.
- Al agrupar variantes equivalentes, la salida conserva como nombre visible la primera variante encontrada en los registros ordenados.

## PDF general

Se habilita con al menos un registro incluido y sin duplicados, campos obligatorios faltantes ni documentos no estándar pendientes de autorización. Incluye únicamente registros con `INCLUIR` activo.

**Comportamiento actual de la herramienta:** antes de imprimir, los registros se ordenan por clave normalizada de unidad, luego por primer apellido y primer nombre normalizados, y finalmente por documento. No conserva necesariamente el orden original del Excel; esta es una conducta actual de la herramienta y no una regla aprobada por negocio.

La paginación se calcula por altura física de las filas. El cambio de unidad no fuerza un salto de página y distintas unidades pueden compartir página. El servicio usa una capacidad objetivo de 70 filas, pero textos de unidad envueltos pueden reducir la cantidad efectiva. La fuente corporal es uniforme; `UNIDADES` reduce moderadamente su tamaño antes de envolver texto y normalmente usa hasta dos líneas.

## ZIP por unidad

Además de los requisitos del PDF general, todos los registros incluidos deben tener `UNIDADES`. Se crea un PDF por grupo de unidad normalizada dentro del ZIP. El servicio usa una capacidad objetivo de 25 filas por PDF, con paginación también basada en altura física.

Las entradas se nombran así:

```text
CERTIFICADOS_<UNIDAD>_<dd-mm-aaaa>.pdf
```

El segmento de unidad se sanea para uso como nombre de archivo.
