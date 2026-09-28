import pytest

pytestmark = pytest.mark.django_db


def test_anonimo_no_puede_listar_usuarios(api, usuario):
    assert api.get("/api/v1/admin/users").status_code == 401


def test_no_admin_no_puede_listar_usuarios(cliente_autenticado, usuario):
    assert cliente_autenticado.get("/api/v1/admin/users").status_code == 403


def test_admin_lista_usuarios(admin_autenticado, usuario):
    respuesta = admin_autenticado.get("/api/v1/admin/users")
    assert respuesta.status_code == 200
    correos = [fila["email"] for fila in respuesta.data["results"]]
    assert usuario.email in correos


def test_admin_cambia_rol_de_otro_usuario(admin_autenticado, usuario):
    respuesta = admin_autenticado.patch(
        f"/api/v1/admin/users/{usuario.id}", {"rol": "admin"}, format="json"
    )
    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.rol == "admin"


def test_admin_desactiva_otro_usuario(admin_autenticado, usuario):
    respuesta = admin_autenticado.patch(
        f"/api/v1/admin/users/{usuario.id}", {"is_active": False}, format="json"
    )
    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.is_active is False


def test_admin_no_puede_cambiar_su_propio_rol(admin_autenticado, usuario_admin):
    respuesta = admin_autenticado.patch(
        f"/api/v1/admin/users/{usuario_admin.id}", {"rol": "cliente"}, format="json"
    )
    assert respuesta.status_code == 400


def test_admin_crea_usuario_nuevo(admin_autenticado):
    respuesta = admin_autenticado.post(
        "/api/v1/admin/users",
        {
            "email": "nuevo@cine.mx",
            "nombre": "Nuevo",
            "apellido": "Empleado",
            "rol": "admin",
            "password": "Cine2026!segura",
        },
        format="json",
    )
    assert respuesta.status_code == 201
    assert respuesta.data["rol"] == "admin"
    assert "password" not in respuesta.data


def test_no_admin_no_puede_crear_usuario(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        "/api/v1/admin/users",
        {"email": "x@x.com", "nombre": "X", "apellido": "Y", "password": "Cine2026!segura"},
        format="json",
    )
    assert respuesta.status_code == 403


def test_no_crea_usuario_con_email_repetido(admin_autenticado, usuario):
    respuesta = admin_autenticado.post(
        "/api/v1/admin/users",
        {
            "email": usuario.email,
            "nombre": "Duplicado",
            "apellido": "Correo",
            "password": "Cine2026!segura",
        },
        format="json",
    )
    assert respuesta.status_code == 400
