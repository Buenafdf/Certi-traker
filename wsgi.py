"""
Punto de entrada WSGI para PythonAnywhere.

Instrucciones:
1. En el panel Web de PythonAnywhere, apunta el archivo WSGI a este archivo.
2. Asegúrate de haber configurado las variables de entorno en el panel
   (o descomenta la sección de carga de .env de abajo).
3. Ajusta RUTA_PROYECTO con la ruta real en PythonAnywhere.
"""
import sys
import os

# ── Ajusta esta ruta a la ruta real de tu proyecto en PythonAnywhere ──────────
RUTA_PROYECTO = "/home/TU_USUARIO/certi-tracker"
# ─────────────────────────────────────────────────────────────────────────────

if RUTA_PROYECTO not in sys.path:
    sys.path.insert(0, RUTA_PROYECTO)

# Opción: cargar variables de entorno desde un archivo .env local
# (útil si prefieres no usar el panel de PythonAnywhere)
#
# from pathlib import Path
# env_file = Path(RUTA_PROYECTO) / ".env"
# if env_file.exists():
#     for line in env_file.read_text().splitlines():
#         line = line.strip()
#         if line and not line.startswith("#") and "=" in line:
#             k, _, v = line.partition("=")
#             os.environ.setdefault(k.strip(), v.strip())

from app import app as application  # noqa: E402

