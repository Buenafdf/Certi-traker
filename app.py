# =============================================================
# Certi-Tracker · Gestor de Cursos
# Backend Flask con SQLite, login de un solo usuario y CSRF.
# =============================================================

import hmac
import os
import secrets
import sqlite3
import time
from collections import defaultdict
from contextlib import closing, contextmanager
from datetime import timedelta
from functools import wraps

from flask import (
    Flask,
    abort,
    after_this_request,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

# ── Configuración ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "gestor_cursos.db"))

ESTADOS = ["Por iniciar", "En curso", "Completado"]
TIPOS   = ["Gratuito", "De pago"]

# Límites de longitud
_MAX_TITULO      = 255
_MAX_PLATAFORMA  = 100
_MAX_ENLACE      = 2048
_MAX_MOTIVO      = 1000

# ── Protección contra fuerza bruta (en memoria) ────────────────────────────────
_intentos: dict[str, list[float]] = defaultdict(list)
_MAX_INTENTOS  = 5
_VENTANA_SEG   = 300   # 5 minutos


def _ip_bloqueada(ip: str) -> bool:
    """Devuelve True si la IP ha superado el límite de intentos."""
    ahora = time.time()
    _intentos[ip] = [t for t in _intentos[ip] if ahora - t < _VENTANA_SEG]
    return len(_intentos[ip]) >= _MAX_INTENTOS


def _registrar_intento(ip: str) -> None:
    _intentos[ip].append(time.time())


# ── Creación de la app ─────────────────────────────────────────────────────────
app = Flask(__name__)

# SECRET_KEY obligatoria; la app no arranca en producción sin ella.
_secret = os.environ.get("SECRET_KEY", "")
_es_produccion = not os.environ.get("FLASK_DEBUG", "")
if not _secret:
    if _es_produccion:
        raise RuntimeError(
            "SECRET_KEY no configurada. Define la variable de entorno SECRET_KEY."
        )
    # Solo en desarrollo local se usa un valor provisional (nunca en prod).
    _secret = secrets.token_hex(32)

app.secret_key = _secret
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "true").lower() != "false",
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
)


# ── Base de datos ──────────────────────────────────────────────────────────────
def init_db() -> None:
    """Crea las tablas si no existen (se llama una vez al arrancar)."""
    schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(sql)
        conn.commit()


@contextmanager
def get_db():
    """Context manager que abre, entrega y cierra la conexión SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── CSRF ───────────────────────────────────────────────────────────────────────
def _csrf_token() -> str:
    """Devuelve (y crea si no existe) el token CSRF de la sesión."""
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


@app.context_processor
def _inyectar_csrf():
    return {"csrf_token": _csrf_token()}


@app.before_request
def _verificar_csrf():
    """Verifica el token CSRF en toda petición POST."""
    if request.method != "POST":
        return
    # Las rutas de login también se protegen (el formulario incluye el token).
    token_sesion = session.get("_csrf", "")
    token_form   = request.form.get("_csrf_token", "")
    if not token_sesion or not hmac.compare_digest(token_sesion, token_form):
        abort(403)


# ── Cabeceras de seguridad ─────────────────────────────────────────────────────
@app.after_request
def _cabeceras_seguridad(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["Referrer-Policy"]          = "strict-origin-when-cross-origin"
    # CSP: permite Google Fonts, archivos estáticos propios y nonce inline si fuera necesario.
    # El script inline de index.html se movió a static/app.js, por lo que 'unsafe-inline' no es necesario.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "script-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'none'; "
        "frame-ancestors 'none';"
    )
    return response


# ── Manejo de errores ──────────────────────────────────────────────────────────
@app.errorhandler(403)
def error_403(e):
    return render_template("error.html", codigo=403, mensaje="Acceso denegado."), 403


@app.errorhandler(404)
def error_404(e):
    return render_template("error.html", codigo=404, mensaje="Página no encontrada."), 404


@app.errorhandler(500)
def error_500(e):
    return render_template("error.html", codigo=500, mensaje="Error interno del servidor."), 500


# ── Decorador login_required ───────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if not session.get("autenticado"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorado


# ── Validaciones ───────────────────────────────────────────────────────────────
def _url_segura(url: str) -> bool:
    """Acepta solo URLs vacías o que comiencen con http:// o https://."""
    if not url:
        return True
    return url.startswith("http://") or url.startswith("https://")


def _next_seguro(next_url: str | None) -> str:
    """Valida que el parámetro next sea una ruta interna (evita open redirect)."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for("index")


def _datos_formulario():
    """Extrae y valida los campos del formulario de curso."""
    titulo           = request.form.get("titulo", "").strip()[:_MAX_TITULO]
    plataforma       = request.form.get("plataforma", "").strip()[:_MAX_PLATAFORMA]
    tipo             = request.form.get("tipo", "").strip()
    estado           = request.form.get("estado", "Por iniciar").strip()
    link_curso       = request.form.get("link_curso", "").strip()[:_MAX_ENLACE]
    link_certificado = request.form.get("link_certificado", "").strip()[:_MAX_ENLACE]

    errores = []
    if not titulo:
        errores.append("El título del curso es obligatorio.")
    if tipo and tipo not in TIPOS:
        errores.append("El tipo indicado no es válido.")
    if estado not in ESTADOS:
        errores.append("El estado indicado no es válido.")
    if not _url_segura(link_curso):
        errores.append("El enlace del curso debe comenzar con http:// o https://.")
    if not _url_segura(link_certificado):
        errores.append("El enlace del certificado debe comenzar con http:// o https://.")

    return {
        "titulo":           titulo,
        "plataforma":       plataforma,
        "tipo":             tipo,
        "estado":           estado,
        "link_curso":       link_curso,
        "link_certificado": link_certificado,
        "errores":          errores,
    }


# ── Rutas de autenticación ─────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("autenticado"):
        return redirect(url_for("index"))

    next_url = request.args.get("next") or request.form.get("next", "")
    error    = None

    if request.method == "POST":
        ip = request.remote_addr or "desconocido"

        if _ip_bloqueada(ip):
            error = "Demasiados intentos fallidos. Espera 5 minutos e inténtalo de nuevo."
        else:
            contrasena   = request.form.get("contrasena", "")
            hash_guardado = os.environ.get("APP_PASSWORD_HASH", "")

            # Pequeño retraso para dificultar ataques de temporización
            time.sleep(0.3)

            if hash_guardado and check_password_hash(hash_guardado, contrasena):
                session.clear()
                session["autenticado"] = True
                session.permanent = True
                return redirect(_next_seguro(next_url))
            else:
                _registrar_intento(ip)
                error = "Contraseña incorrecta."

    return render_template("login.html", error=error, next=next_url)


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Rutas principales ──────────────────────────────────────────────────────────
@app.route("/")
@login_required
def index():
    with get_db() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id, titulo, plataforma, tipo, estado, "
                "link_curso, link_certificado, "
                "strftime('%d/%m/%Y %H:%M', fecha_registro) AS fecha "
                "FROM cursos_certificados ORDER BY id DESC"
            )
            rows = [dict(r) for r in cur.fetchall()]

    resumen = {
        "total":      len(rows),
        "en_curso":   sum(1 for r in rows if r["estado"] == "En curso"),
        "completados": sum(1 for r in rows if r["estado"] == "Completado"),
        "por_iniciar": sum(1 for r in rows if r["estado"] == "Por iniciar"),
    }
    return render_template("index.html", cursos=rows, resumen=resumen)


@app.route("/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_curso():
    if request.method == "POST":
        datos = _datos_formulario()
        for msg in datos["errores"]:
            flash(msg, "error")
        if datos["errores"]:
            return redirect(url_for("nuevo_curso"))

        with get_db() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "INSERT INTO cursos_certificados "
                    "(titulo, plataforma, tipo, estado, link_curso, link_certificado) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (datos["titulo"], datos["plataforma"], datos["tipo"],
                     datos["estado"], datos["link_curso"], datos["link_certificado"]),
                )

        flash("Curso registrado correctamente.", "success")
        return redirect(url_for("index"))

    return render_template("nuevo_curso.html", estados=ESTADOS, tipos=TIPOS, curso={})


@app.route("/editar/<int:curso_id>", methods=["GET", "POST"])
@login_required
def editar_curso(curso_id):
    with get_db() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT * FROM cursos_certificados WHERE id = ?", (curso_id,)
            )
            row = cur.fetchone()
            if row is None:
                flash("El curso no existe.", "error")
                return redirect(url_for("index"))
            curso = dict(row)

    if request.method == "POST":
        datos = _datos_formulario()
        for msg in datos["errores"]:
            flash(msg, "error")
        if datos["errores"]:
            return redirect(url_for("editar_curso", curso_id=curso_id))

        with get_db() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "UPDATE cursos_certificados SET "
                    "titulo = ?, plataforma = ?, tipo = ?, estado = ?, "
                    "link_curso = ?, link_certificado = ? WHERE id = ?",
                    (datos["titulo"], datos["plataforma"], datos["tipo"],
                     datos["estado"], datos["link_curso"], datos["link_certificado"],
                     curso_id),
                )

        flash("Curso actualizado correctamente.", "success")
        return redirect(url_for("index"))

    return render_template("nuevo_curso.html", curso=curso, estados=ESTADOS, tipos=TIPOS)


@app.route("/eliminar/<int:curso_id>", methods=["POST"])
@login_required
def eliminar_curso(curso_id):
    motivo = request.form.get("motivo", "").strip()[:_MAX_MOTIVO]
    if not motivo:
        flash("Debes indicar el motivo de la eliminación.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT titulo FROM cursos_certificados WHERE id = ?", (curso_id,)
            )
            fila = cur.fetchone()
            if fila is None:
                flash("El curso no existe.", "error")
                return redirect(url_for("index"))
            titulo = fila["titulo"]

            # INSERT y DELETE en la misma transacción (get_db hace commit al salir)
            cur.execute(
                "INSERT INTO registro_eliminaciones (curso_titulo, motivo) VALUES (?, ?)",
                (titulo, motivo),
            )
            cur.execute(
                "DELETE FROM cursos_certificados WHERE id = ?", (curso_id,)
            )

    flash(f'Curso "{titulo}" eliminado. Motivo registrado.', "warning")
    return redirect(url_for("index"))


@app.route("/historial")
@login_required
def historial():
    with get_db() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id, curso_titulo, motivo, "
                "strftime('%d/%m/%Y %H:%M', fecha_eliminacion) AS fecha "
                "FROM registro_eliminaciones ORDER BY id DESC"
            )
            rows = [dict(r) for r in cur.fetchall()]
    return render_template("historial.html", eliminaciones=rows)


@app.route("/exportar-csv")
@login_required
def exportar_csv():
    """Exporta todos los cursos a CSV."""
    import csv
    import io
    from flask import Response

    with get_db() as conn:
        with closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT id, titulo, plataforma, tipo, estado, "
                "link_curso, link_certificado, "
                "strftime('%d/%m/%Y %H:%M', fecha_registro) AS fecha_registro "
                "FROM cursos_certificados ORDER BY id"
            )
            filas = cur.fetchall()

    salida = io.StringIO()
    escritor = csv.writer(salida)
    escritor.writerow(["ID", "Título", "Plataforma", "Tipo", "Estado",
                        "Enlace curso", "Enlace certificado", "Fecha registro"])
    for f in filas:
        escritor.writerow(list(f))

    return Response(
        salida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=cursos.csv"},
    )


# ── Arranque ───────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

if __name__ == "__main__":
    _debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(port=5000, debug=_debug)
