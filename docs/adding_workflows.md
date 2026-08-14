# Cómo agregar un workflow

La aplicación usa un registro explícito. Un workflow aporta metadata y una vista `QWidget`; sus reglas internas son independientes de los demás flujos.

## Pasos

1. Crear `workflows/<id_del_flujo>/` con `__init__.py`.
2. Implementar una vista que herede de `PySide6.QtWidgets.QWidget` en `view.py`.
3. Crear `service.py` si el flujo necesita reglas o coordinación propias. No importar internals de otros workflows.
4. Declarar `metadata.py`:

   ```python
   from app.workflow_contract import WorkflowDefinition
   from workflows.nuevo_flujo.view import NuevoFlujoView

   workflow_definition = WorkflowDefinition(
       id="nuevo_flujo",
       name="Nuevo flujo",
       description="Descripción breve del flujo.",
       view_class=NuevoFlujoView,
       enabled=True,
   )
   ```

5. Importar esa definición en `app/workflow_registry.py` y agregarla a la lista que construye `workflow_registry`. El ID debe ser único.
6. Agregar pruebas de metadata, servicio, vista y navegación. Las definiciones simuladas deben existir solo en `tests/`.
7. Guardar assets exclusivos bajo `workflows/<id_del_flujo>/assets/` y resolverlos desde el propio módulo. Los recursos corporativos compartidos permanecen en `assets/`.

## Contrato de integración

`WorkflowDefinition` exige ID, nombre, descripción y una clase `QWidget`. También admite icono, versión y estado habilitado. `MainWindow` crea la vista al primer acceso y reutiliza esa misma instancia durante la sesión.

Una vista puede exponer opcionalmente una señal `activity_changed(str)` para la barra de estado y una propiedad booleana `is_busy` para impedir el cierre durante operaciones. Estas extensiones son de integración UI; el contrato no impone operaciones de negocio como Excel, PDF o ZIP.

Si la construcción falla, la aplicación registra `workflow=<id> operation=load status=failed`, muestra un mensaje recuperable y vuelve a Inicio.
