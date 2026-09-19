# ============================================================
# Certi-Tracker · Gestor de Cursos
#
# RED PRIVADA TAILSCALE
# ---------------------
# El servidor ALVAROSV14 (Tailscale: 100.70.90.19) es el que:
#   - HOSTEA SQL Server (instancia por defecto,
#     base de datos: GestorCursos, autenticacion Windows).
#   - EJECUTA esta aplicacion Flask en http://0.0.0.0:5000.
#
# Como se accede desde cada nodo (todos en la misma Tailnet):
#   - Laptop (alvaro14, 100.105.54.80): http://100.70.90.19:5000
#   - Movil  (a04-de-alvaro, 100.79.76.1): http://100.70.90.19:5000
#   - El propio servidor: http://127.0.0.1:5000
#
# Para ADAPTAR la conexion a SQL Server, solo toca la variable SERVER:
#   - SERVER = "ALVAROSV14"        # nombre del host en tu red local
#   - SERVER = "100.70.90.19"      # IP Tailscale del servidor SQL
#   - SERVER = "localhost"         # si la app corre en el mismo equipo
#                                  #   que SQL Server (caso actual)
#   - SERVER = "ALVAROSV14,1433"   # con puerto explicito
#
# IMPORTANTE: si ejecutas la app desde OTRO nodo (laptop, movil)
# apuntando al SQL de ALVAROSV14 por Tailscale, la autenticacion
# Windows (Trusted_Connection=yes) puede fallar porque se intenta
# validar tu cuenta de Windows contra la maquina remota. En ese
# caso usa una cuenta SQL con UID/PWD (ver get_connection()).
# La forma recomendada es ejecutar la app EN ALVAROSV14 y entrar
# desde los demas dispositivos por su IP Tailscale.
# ============================================================

import os

import pyodbc
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambiame-en-produccion")

SERVER = "ALVAROSV14"
DATABASE = "GestorCursos"
DB_DRIVER = "ODBC Driver 17 for SQL Server"

ESTADOS = ["Por iniciar", "En curso", "Completado"]
TIPOS = ["Gratuito", "De pago"]


def get_connection():
    return pyodbc.connect(
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )


# Si SQL Server usa autenticacion SQL (usuario/contraseña) en lugar de Windows:
#
# def get_connection():
#     return pyodbc.connect(
#         f"DRIVER={{{DB_DRIVER}}};"
#         f"SERVER={SERVER};"
#         f"DATABASE={DATABASE};"
#         f"UID={os.environ.get('DB_USER')};"
#         f"PWD={os.environ.get('DB_PASSWORD')};"
#         "TrustServerCertificate=yes;",
#     )


@app.route("/")
def index():
    rows = []
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, titulo, plataforma, tipo, estado, "
            "link_curso, link_certificado, "
            "FORMAT(fecha_registro, 'dd/MM/yyyy HH:mm') AS fecha "
            "FROM dbo.cursos_certificados ORDER BY id DESC"
        )
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

    resumen = {
        "total": len(rows),
        "en_curso": sum(1 for r in rows if r["estado"] == "En curso"),
        "completados": sum(1 for r in rows if r["estado"] == "Completado"),
        "por_iniciar": sum(1 for r in rows if r["estado"] == "Por iniciar"),
    }
    return render_template("index.html", cursos=rows, resumen=resumen)


@app.route("/nuevo", methods=["GET", "POST"])
def nuevo_curso():
    if request.method == "POST":
        datos = _datos_formulario()
        if not datos["titulo"]:
            flash("El título del curso es obligatorio.", "error")
            return redirect(url_for("nuevo_curso"))

        with get_connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO dbo.cursos_certificados "
                "(titulo, plataforma, tipo, estado, link_curso, link_certificado) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                datos["titulo"],
                datos["plataforma"],
                datos["tipo"],
                datos["estado"],
                datos["link_curso"],
                datos["link_certificado"],
            )
            conn.commit()

        flash("Curso registrado correctamente.", "success")
        return redirect(url_for("index"))

    return render_template(
        "nuevo_curso.html", estados=ESTADOS, tipos=TIPOS, curso={}
    )


@app.route("/editar/<int:curso_id>", methods=["GET", "POST"])
def editar_curso(curso_id):
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM dbo.cursos_certificados WHERE id = ?", curso_id
        )
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        if row is None:
            flash("El curso no existe.", "error")
            return redirect(url_for("index"))
        curso = dict(zip(columns, row))

    if request.method == "POST":
        datos = _datos_formulario()
        if not datos["titulo"]:
            flash("El título del curso es obligatorio.", "error")
            return redirect(url_for("editar_curso", curso_id=curso_id))

        with get_connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "UPDATE dbo.cursos_certificados SET "
                "titulo = ?, plataforma = ?, tipo = ?, estado = ?, "
                "link_curso = ?, link_certificado = ? WHERE id = ?",
                datos["titulo"],
                datos["plataforma"],
                datos["tipo"],
                datos["estado"],
                datos["link_curso"],
                datos["link_certificado"],
                curso_id,
            )
            conn.commit()

        flash("Curso actualizado correctamente.", "success")
        return redirect(url_for("index"))

    return render_template(
        "nuevo_curso.html", curso=curso, estados=ESTADOS, tipos=TIPOS
    )


@app.route("/eliminar/<int:curso_id>", methods=["POST"])
def eliminar_curso(curso_id):
    motivo = request.form.get("motivo", "").strip()
    if not motivo:
        flash("Debes indicar el motivo de la eliminación.", "error")
        return redirect(url_for("index"))

    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT titulo FROM dbo.cursos_certificados WHERE id = ?", curso_id
        )
        fila = cursor.fetchone()
        if fila is None:
            flash("El curso no existe.", "error")
            return redirect(url_for("index"))
        titulo = fila[0]

        cursor.execute(
            "INSERT INTO dbo.registro_eliminaciones (curso_titulo, motivo) "
            "VALUES (?, ?)",
            titulo,
            motivo,
        )
        cursor.execute(
            "DELETE FROM dbo.cursos_certificados WHERE id = ?", curso_id
        )
        conn.commit()

    flash(f"Curso \"{titulo}\" eliminado. Motivo registrado.", "warning")
    return redirect(url_for("index"))


@app.route("/historial")
def historial():
    rows = []
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, curso_titulo, motivo, "
            "FORMAT(fecha_eliminacion, 'dd/MM/yyyy HH:mm') AS fecha "
            "FROM dbo.registro_eliminaciones ORDER BY id DESC"
        )
        columns = [column[0] for column in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return render_template("historial.html", eliminaciones=rows)


def _datos_formulario():
    return {
        "titulo": request.form.get("titulo", "").strip(),
        "plataforma": request.form.get("plataforma", "").strip(),
        "tipo": request.form.get("tipo", "").strip(),
        "estado": request.form.get("estado", "Por iniciar").strip(),
        "link_curso": request.form.get("link_curso", "").strip(),
        "link_certificado": request.form.get("link_certificado", "").strip(),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)