#!/usr/bin/env python3
"""
Script de migración única: SQL Server → SQLite.

Ejecutar UNA vez en el equipo donde está SQL Server instalado.
Requiere: pip install pyodbc (ver requirements-migracion.txt)

Uso:
    python scripts/migrar_sqlserver_a_sqlite.py

Variables de entorno opcionales:
    MSSQL_SERVER   - nombre del servidor SQL Server (por defecto: ALVAROSV14)
    MSSQL_DB       - nombre de la base de datos (por defecto: GestorCursos)
    DB_PATH        - ruta del archivo SQLite destino (por defecto: gestor_cursos.db junto al script)
"""
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc no está instalado. Ejecuta: pip install pyodbc")
    sys.exit(1)

# ── Configuración ──────────────────────────────────────────────────────────────
SERVER   = os.environ.get("MSSQL_SERVER", "ALVAROSV14")
DATABASE = os.environ.get("MSSQL_DB", "GestorCursos")
DRIVER   = "ODBC Driver 17 for SQL Server"

# Ruta absoluta del .db en el directorio padre del script (raíz del proyecto)
_BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH   = os.environ.get("DB_PATH", str(_BASE_DIR / "gestor_cursos.db"))

SCHEMA_SQL = _BASE_DIR / "database" / "schema.sql"


def conectar_sqlserver():
    """Devuelve una conexión a SQL Server."""
    return pyodbc.connect(
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


def init_sqlite(sqlite_conn):
    """Crea las tablas en SQLite si no existen."""
    schema = SCHEMA_SQL.read_text(encoding="utf-8")
    sqlite_conn.executescript(schema)
    sqlite_conn.commit()


def copiar_cursos(src_cursor, dst_conn):
    """Copia la tabla cursos_certificados; idempotente por id."""
    src_cursor.execute(
        "SELECT id, titulo, plataforma, tipo, estado, "
        "link_curso, link_certificado, "
        "FORMAT(fecha_registro, 'yyyy-MM-dd HH:mm:ss') AS fecha_registro "
        "FROM dbo.cursos_certificados ORDER BY id"
    )
    filas = src_cursor.fetchall()
    insertados = 0
    with closing(dst_conn.cursor()) as c:
        for f in filas:
            existente = c.execute(
                "SELECT 1 FROM cursos_certificados WHERE id = ?", (f[0],)
            ).fetchone()
            if not existente:
                c.execute(
                    "INSERT INTO cursos_certificados "
                    "(id, titulo, plataforma, tipo, estado, link_curso, link_certificado, fecha_registro) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (f[0], f[1], f[2], f[3], f[4], f[5], f[6], f[7])
                )
                insertados += 1
        dst_conn.commit()
    print(f"  cursos_certificados: {insertados} filas nuevas copiadas de {len(filas)} totales.")
    return insertados


def copiar_eliminaciones(src_cursor, dst_conn):
    """Copia la tabla registro_eliminaciones; idempotente por id."""
    src_cursor.execute(
        "SELECT id, curso_titulo, motivo, "
        "FORMAT(fecha_eliminacion, 'yyyy-MM-dd HH:mm:ss') AS fecha_eliminacion "
        "FROM dbo.registro_eliminaciones ORDER BY id"
    )
    filas = src_cursor.fetchall()
    insertados = 0
    with closing(dst_conn.cursor()) as c:
        for f in filas:
            existente = c.execute(
                "SELECT 1 FROM registro_eliminaciones WHERE id = ?", (f[0],)
            ).fetchone()
            if not existente:
                c.execute(
                    "INSERT INTO registro_eliminaciones "
                    "(id, curso_titulo, motivo, fecha_eliminacion) "
                    "VALUES (?, ?, ?, ?)",
                    (f[0], f[1], f[2], f[3])
                )
                insertados += 1
        dst_conn.commit()
    print(f"  registro_eliminaciones: {insertados} filas nuevas copiadas de {len(filas)} totales.")
    return insertados


def main():
    print(f"Conectando a SQL Server: {SERVER}/{DATABASE} …")
    try:
        src_conn = conectar_sqlserver()
    except Exception as e:
        print(f"ERROR al conectar a SQL Server: {e}")
        sys.exit(1)

    print(f"Abriendo/creando SQLite en: {DB_PATH}")
    with closing(sqlite3.connect(DB_PATH)) as dst_conn:
        init_sqlite(dst_conn)
        with closing(src_conn.cursor()) as cur:
            print("Migrando datos …")
            copiar_cursos(cur, dst_conn)
            copiar_eliminaciones(cur, dst_conn)

    src_conn.close()
    print("Migración completada con éxito.")


if __name__ == "__main__":
    main()

