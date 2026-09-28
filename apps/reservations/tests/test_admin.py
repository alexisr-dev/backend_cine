from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.reservations.models import Reserva

pytestmark = pytest.mark.django_db


@pytest.fixture
def reserva(usuario, funcion):
    return Reserva.objects.create(
        codigo_reserva="RSV-ADMIN-1",
        usuario=usuario,
        funcion=funcion,
        total=Decimal("100.00"),
        expira_en=timezone.now() + timedelta(minutes=10),
    )


def test_anonimo_no_puede_listar(api, reserva):
    respuesta = api.get("/api/v1/admin/reservations")
    assert respuesta.status_code == 401


def test_no_admin_no_puede_listar(cliente_autenticado, reserva):
    respuesta = cliente_autenticado.get("/api/v1/admin/reservations")
    assert respuesta.status_code == 403


def test_admin_lista_todas_las_reservas_con_email(admin_autenticado, reserva):
    respuesta = admin_autenticado.get("/api/v1/admin/reservations")
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["usuario_email"] == reserva.usuario.email


def test_admin_puede_cancelar_reserva_de_otro_usuario(admin_autenticado, reserva):
    respuesta = admin_autenticado.delete(f"/api/v1/reservations/{reserva.id}")
    assert respuesta.status_code == 200
    reserva.refresh_from_db()
    assert reserva.estado == "cancelada"
