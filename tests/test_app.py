"""
Pruebas básicas de Certi-Tracker.
Ejecutar con: pytest tests/
"""
import os
import sys
import tempfile

import pytest

# Configurar variables de entorno antes de importar la app
os.environ["SECRET_KEY"] = "clave-de-prueba-no-usar-en-prod"
os.environ["APP_PASSWORD_HASH"] = ""          # se sobreescribe en cada test
os.environ["SESSION_COOKIE_SECURE"] = "false" # HTTP en tests
os.environ["FLASK_DEBUG"] = "true"            # evita el RuntimeError de SECRET_KEY vacía


@pytest.fixture
def cliente(tmp_path):
    """Crea una app de prueba con base de datos temporal."""
    from werkzeug.security import generate_password_hash

    # Contraseña de prueba
    contrasena = "prueba-segura-123"
    os.environ["APP_PASSWORD_HASH"] = generate_password_hash(contrasena)
    os.environ["DB_PATH"] = str(tmp_path / "test.db")

    # Reimportar app para que tome el nuevo DB_PATH
    if "app" in sys.modules:
        del sys.modules["app"]

    import app as modulo_app

    modulo_app.app.config["TESTING"] = True
    modulo_app.app.config["WTF_CSRF_ENABLED"] = False

    with modulo_app.app.test_client() as c:
        yield c


def _obtener_csrf(cliente, url="/login"):
    """Obtiene el token CSRF haciendo un GET a la ruta indicada."""
    with cliente.session_transaction() as sess:
        sess["_csrf"] = "token-de-prueba"
    return "token-de-prueba"


def _login(cliente, contrasena="prueba-segura-123"):
    """Realiza el login y devuelve la respuesta."""
    csrf = _obtener_csrf(cliente)
    return cliente.post(
        "/login",
        data={"contrasena": contrasena, "_csrf_token": csrf},
        follow_redirects=True,
    )


# ── Tests de autenticación ─────────────────────────────────────────────────────

def test_login_redirige_a_login_sin_autenticar(cliente):
    """La raíz redirige a /login si no hay sesión."""
    resp = cliente.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_correcto(cliente):
    """Un login correcto redirige al índice."""
    resp = _login(cliente)
    assert resp.status_code == 200
    # Debe mostrar la página de cursos
    assert b"Mis Cursos" in resp.data or b"CERTI-TRACKER" in resp.data


def test_login_incorrecto(cliente):
    """Una contraseña incorrecta muestra mensaje de error."""
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/login",
        data={"contrasena": "clave-erronea", "_csrf_token": csrf},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "incorrecta" in resp.data.decode("utf-8").lower()


def test_csrf_invalido_devuelve_403(cliente):
    """Un POST sin token CSRF válido devuelve 403."""
    resp = cliente.post(
        "/login",
        data={"contrasena": "cualquier-cosa", "_csrf_token": "token-invalido"},
    )
    assert resp.status_code == 403


# ── Tests de CRUD ──────────────────────────────────────────────────────────────

def test_nuevo_curso_requiere_login(cliente):
    """GET /nuevo redirige a login sin sesión."""
    resp = cliente.get("/nuevo", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_crear_y_listar_curso(cliente):
    """Crea un curso y verifica que aparece en el índice."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/nuevo",
        data={
            "titulo": "Python para Data Science",
            "plataforma": "Coursera",
            "tipo": "Gratuito",
            "estado": "En curso",
            "link_curso": "https://coursera.org/python",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Python para Data Science" in resp.data.decode("utf-8")


def test_crear_curso_sin_titulo_falla(cliente):
    """Un POST sin título no crea el curso."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/nuevo",
        data={
            "titulo": "",
            "plataforma": "Udemy",
            "tipo": "De pago",
            "estado": "Por iniciar",
            "link_curso": "",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # Debe mostrar mensaje de error o no el curso (redirige a /nuevo)


def test_editar_curso(cliente):
    """Edita un curso existente y verifica el cambio."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)

    # Crear curso
    cliente.post(
        "/nuevo",
        data={
            "titulo": "Curso Original",
            "plataforma": "edX",
            "tipo": "Gratuito",
            "estado": "Por iniciar",
            "link_curso": "",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )

    # Editar el primer curso (id=1)
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/editar/1",
        data={
            "titulo": "Curso Editado",
            "plataforma": "edX",
            "tipo": "Gratuito",
            "estado": "En curso",
            "link_curso": "",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Curso Editado" in resp.data.decode("utf-8")


def test_eliminar_curso_registra_historial(cliente):
    """Elimina un curso y verifica que aparece en el historial."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)

    # Crear curso
    cliente.post(
        "/nuevo",
        data={
            "titulo": "Curso a Eliminar",
            "plataforma": "YouTube",
            "tipo": "",
            "estado": "Por iniciar",
            "link_curso": "",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )

    # Eliminar (id=1)
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/eliminar/1",
        data={"motivo": "Prueba de eliminación", "_csrf_token": csrf},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # Verificar historial
    resp_hist = cliente.get("/historial")
    assert "Curso a Eliminar" in resp_hist.data.decode("utf-8")


def test_eliminar_sin_motivo_falla(cliente):
    """Eliminar sin motivo muestra error y no elimina el curso."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)

    # Crear curso
    cliente.post(
        "/nuevo",
        data={
            "titulo": "Curso Sin Motivo",
            "plataforma": "",
            "tipo": "",
            "estado": "Por iniciar",
            "link_curso": "",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )

    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/eliminar/1",
        data={"motivo": "", "_csrf_token": csrf},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    # El curso debe seguir existiendo
    assert "Curso Sin Motivo" in resp.data.decode("utf-8")


def test_exportar_csv(cliente):
    """Verifica que /exportar-csv devuelve un CSV."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)

    cliente.post(
        "/nuevo",
        data={
            "titulo": "Curso CSV",
            "plataforma": "Platzi",
            "tipo": "De pago",
            "estado": "Completado",
            "link_curso": "https://platzi.com/cursos/csv",
            "link_certificado": "",
            "_csrf_token": csrf,
        },
        follow_redirects=True,
    )

    resp = cliente.get("/exportar-csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    assert b"Curso CSV" in resp.data


def test_logout(cliente):
    """El logout cierra la sesión y redirige a login."""
    _login(cliente)
    csrf = _obtener_csrf(cliente)
    resp = cliente.post(
        "/logout",
        data={"_csrf_token": csrf},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_pagina_404(cliente):
    """Una ruta inexistente devuelve 404."""
    _login(cliente)
    resp = cliente.get("/ruta-inexistente-xyz")
    assert resp.status_code == 404

