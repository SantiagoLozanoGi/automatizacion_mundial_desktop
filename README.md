# Automatización Mundial

Plataforma modular de escritorio para automatizar procesos de Mundial de Seguros. **Certificados ICBF** es actualmente el primer y único workflow implementado.

## Arquitectura

- `app/`: ventana principal, registro de workflows, logging y file IO comunes.
- `config/`: nombre, identificador y resolución de recursos de la aplicación.
- `workflows/certificados_icbf/`: vista, modelos y servicio exclusivos del flujo ICBF.
- `workflows/certificados_icbf/legacy/`: lógica heredada protegida.
- `assets/`: recursos visuales compartidos.
- `tests/`: regresión, servicios, modelos, UI y registro modular.
- `docs/adding_workflows.md`: guía para incorporar un flujo futuro.

La navegación e Inicio se generan desde `app/workflow_registry.py`. Cada vista se crea al entrar por primera vez y se conserva durante la sesión, evitando reprocesamiento y pérdida de estado.

## Desarrollo

```powershell
python -m pytest -q
python main.py
```

Las reglas de negocio ICBF permanecen dentro de su módulo. Las capacidades compartidas pertenecen a `app/`; ningún workflow debe depender de internals privados de otro.
