import pytest

pytestmark = pytest.mark.django_db


def test_registro_devuelve_tokens(api):
    respuesta = api.post(
        "/api/v1/auth/register",
        {
            "email": "Nuevo@Cine.mx",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "password": "ClaveSegura2026",
            "password_confirm": "ClaveSegura2026",
        },
        format="json",
    )
    assert respuesta.status_code == 201
    assert respuesta.data["usuario"]["email"] == "nuevo@cine.mx"
    assert respuesta.data["access"]
    assert respuesta.data["refresh"]


def test_registro_rechaza_email_duplicado(api, usuario):
    respuesta = api.post(
        "/api/v1/auth/register",
        {
            "email": usuario.email,
            "nombre": "Otro",
            "apellido": "Usuario",
            "password": "ClaveSegura2026",
            "password_confirm": "ClaveSegura2026",
        },
        format="json",
    )
    assert respuesta.status_code == 400


def test_login_incluye_perfil(api, usuario):
    respuesta = api.post(
        "/api/v1/auth/login",
        {"email": usuario.email, "password": "Cine2026!"},
        format="json",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["usuario"]["nombre"] == "Cliente"


def test_perfil_requiere_token(api):
    assert api.get("/api/v1/auth/me").status_code == 401


def test_perfil_con_token(cliente_autenticado, usuario):
    respuesta = cliente_autenticado.get("/api/v1/auth/me")
    assert respuesta.status_code == 200
    assert respuesta.data["email"] == usuario.email
