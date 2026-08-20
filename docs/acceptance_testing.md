# Protocolo de pruebas de aceptación

Este protocolo permite evaluar la versión entregada sin usar datos personales reales en esta documentación.

## Preparación

```text
Versión de aplicación:
Fecha:
Equipo:
Responsable:
Archivo de entrada:
Resultado manual de referencia:
```

Use una copia controlada del archivo de prueba y conserve los resultados generados. Consulte [Reglas de negocio vigentes](business_rules.md) para distinguir un defecto de una regla implementada.

## Casos mínimos

| Área | Caso | Resultado esperado | Resultado / evidencia |
| --- | --- | --- | --- |
| Procesamiento | Excel válido | Se procesa y muestra registros. | |
| Procesamiento | Excel sin `UNIDADES` | Se procesa; el campo queda vacío y editable. | |
| Procesamiento | Novedad `IN` | La fila se conserva. | |
| Procesamiento | Novedad `INGRESO` | La fila se conserva. | |
| Procesamiento | Novedad `INGRES0` | La fila se conserva. | |
| Procesamiento | Novedad `1NGRESO` | La fila se conserva. | |
| Procesamiento | Novedad no válida | La fila se excluye. | |
| Validación | Documento estándar | No produce anomalía documental. | |
| Validación | Documento no estándar | Bloquea hasta autorización explícita. | |
| Validación | Autorizar y revocar | Autorizar permite continuar; revocar vuelve a bloquear. | |
| Validación | Documento duplicado | Las filas duplicadas incluidas bloquean. | |
| Validación | Campo obligatorio faltante | Bloquea y aparece en reporte. | |
| UNIDADES | Unidad presente | Permite ZIP si no hay otros bloqueos. | |
| UNIDADES | Unidad vacía | PDF general permitido; ZIP bloqueado. | |
| UNIDADES | Edición manual | Actualiza disponibilidad del ZIP. | |
| UNIDADES | Completar unidad | Habilita ZIP si no hay otros bloqueos. | |
| Salidas | PDF general | Se guarda y contiene solo incluidos. | |
| Salidas | ZIP | Contiene un PDF por unidad normalizada. | |
| Salidas | Duplicados y campos faltantes | Genera reportes cuando existen anomalías. | |
| Salidas | Texto de correo | Puede actualizarse y copiarse. | |

## Comparación con resultado manual

```text
Total registros entrada:
Total registros esperado:
Total registros herramienta:

Documentos coincidentes:
Faltantes:
Adicionales:

Páginas manual:
Páginas herramienta:

Diferencia de orden: Sí / No
Diferencia visual: Sí / No

Diferencias funcionales:
```

Clasifique cada hallazgo con una o más etiquetas:

```text
ERROR_HERRAMIENTA
POSIBLE_ERROR_RESULTADO_MANUAL
DIFERENCIA_REGLA_NEGOCIO
DIFERENCIA_ORDEN
DIFERENCIA_FORMATO
DIFERENCIA_PAGINACION
DIFERENCIA_VISUAL
REQUIERE_VALIDACION_HUMANA
```

## Aspectos que deben validarse con negocio

### Ordenamiento

La herramienta ordena internamente por unidad, apellido/nombre y documento. En una prueba anterior, el resultado manual conservaba el orden del Excel. Confirme con el responsable del proceso cuál debe prevalecer.

### Documentos no estándar

La generación se bloquea hasta que una persona autoriza explícitamente cada documento no estándar. Validar si el proceso empresarial desea conservar este control.

### Paginación

La cantidad de páginas puede diferir del resultado manual por la maquetación dinámica. En los PDFs del ZIP, el valor interno `rows_per_page=25` no impone 25 registros por página: la cantidad real depende de la altura disponible y del contenido. La aceptación debe evaluar integridad de registros, legibilidad y ausencia de cortes, no solamente la cantidad exacta de páginas.
