# Build y distribución en Windows

Este procedimiento produce una distribución ONEDIR para Windows.

## Entorno de desarrollo

Desde la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Instalar dependencias de desarrollo

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

## Ejecutar tests

```powershell
python -m pytest -q
```

No continúe con una entrega si la suite presenta fallos.

## Crear entorno limpio de empaquetado

Para generar una distribución reproducible, cree un entorno separado que contenga solo las dependencias de producción y PyInstaller. No use un Python global ni un entorno que contenga herramientas ajenas al proyecto, ya que PyInstaller puede detectar e incluir dependencias instaladas allí.

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install --upgrade pip
.\.venv-build\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.\.venv-build\Scripts\python.exe -m pip check
```

## Limpiar build anterior

Si existen salidas previas de PyInstaller que se van a reemplazar, elimine únicamente las carpetas de salida del build anterior después de verificar su contenido y de conservar cualquier entrega que deba archivarse:

```powershell
Remove-Item -Recurse -Force build\AutomatizacionMundial
Remove-Item -Recurse -Force dist_prueba_empresa\AutomatizacionMundial
```

## Ejecutar PyInstaller

```powershell
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name AutomatizacionMundial --add-data "assets;assets" --exclude-module pytest --distpath dist_prueba_empresa main.py
```

El comando incorpora el directorio `assets` requerido por la aplicación y excluye `pytest` del ejecutable.

## Ruta del ejecutable

```text
dist_prueba_empresa/AutomatizacionMundial/AutomatizacionMundial.exe
```

## Verificación del ONEDIR

1. Confirme que el ejecutable existe dentro de la carpeta ONEDIR.
2. Confirme que la carpeta incluye los archivos y subcarpetas generados junto al ejecutable, incluidos los recursos empaquetados.
3. Abra la aplicación desde esa carpeta y realice una prueba básica de carga, revisión y generación.

## Crear ZIP de distribución

Comprima la carpeta completa `AutomatizacionMundial`, no solo el ejecutable:

```powershell
Compress-Archive -Path dist_prueba_empresa\AutomatizacionMundial -DestinationPath dist_prueba_empresa\AutomatizacionMundial-Windows.zip
```

> El `.exe` no debe distribuirse solo. El usuario debe recibir la carpeta ONEDIR completa o un ZIP que contenga toda esa carpeta.

## Prueba desde carpeta descomprimida

Extraiga el ZIP en una carpeta temporal, abra `AutomatizacionMundial.exe` desde la carpeta extraída y compruebe que la aplicación inicia y puede procesar un archivo de prueba autorizado.

Los directorios `.venv/`, `.venv-build/`, `build/`, `dist/`, `dist_prueba_empresa/`, `build_prueba_limpia/` y `dist_prueba_limpia/` están ignorados por Git.
