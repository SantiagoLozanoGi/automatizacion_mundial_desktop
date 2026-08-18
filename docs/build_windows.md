# Build de Windows

Desde la raíz del proyecto, cree y active el entorno aislado:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Ejecute la suite antes de empaquetar:

```powershell
python -m pytest -q
```

Genere el paquete ONEDIR limpio:

```powershell
python -m PyInstaller --noconfirm --clean --windowed --onedir --name AutomatizacionMundial --add-data "assets;assets" --exclude-module pytest --distpath dist_prueba_empresa main.py
```

El ejecutable queda en `dist_prueba_empresa/AutomatizacionMundial/AutomatizacionMundial.exe`.
Los directorios `.venv/`, `build/`, `dist/` y `dist_prueba_empresa/` están ignorados por Git.

`pytest` se excluye porque el módulo heredado `test_processor.py` vive dentro de
un paquete importable; la exclusión evita que la herramienta de pruebas forme
parte del ejecutable.
