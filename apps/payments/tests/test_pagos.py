from datetime import timedelta

import pytest
from django.utils import timezone

from apps.payments.models import EstadoPago, Pago, Ticket
from apps.reservations.models import EstadoReserva, Reserva
from apps.reservations.services import crear_reserva
from apps.showtimes.models import EstadoFuncionAsiento, FuncionAsiento

pytestmark = pytest.mark.django_db

TARJETA_OK = {
    "metodo_pago": "tarjeta",
    "nombre_titular": "Cliente Demo",
    "numero_tarjeta": "4242424242424242",
    "expiracion": "12/29",
    "cvv": "123",
}


@pytest.fixture
def reserva(usuario, funcion):
    ids = list(FuncionAsiento.objects.filter(funcion=funcion).values_list("id", flat=True))[:2]
    return crear_reserva(usuario, funcion.id, ids)


def test_pago_aprobado_confirma_reserva_y_emite_ticket(cliente_autenticado, reserva):
    respuesta = cliente_autenticado.post(
        f"/api/v1/reservations/{reserva.id}/payment",
        TARJETA_OK,
        format="json",
        HTTP_IDEMPOTENCY_KEY="clave-1",
    )
    assert respuesta.status_code == 201
    assert respuesta.data["pago"]["estado"] == EstadoPago.APROBADO
    assert respuesta.data["reserva"]["estado"] == EstadoReserva.CONFIRMADA

    reserva.refresh_from_db()
    assert Ticket.objects.filter(reserva=reserva).exists()
    assert (
        FuncionAsiento.objects.filter(
            reserva_asientos__reserva=reserva, estado=EstadoFuncionAsiento.OCUPADO
        ).count()
        == 2
    )


def test_idempotencia_no_cobra_dos_veces(cliente_autenticado, reserva):
    for _ in range(3):
        respuesta = cliente_autenticado.post(
            f"/api/v1/reservations/{reserva.id}/payment",
            TARJETA_OK,
            format="json",
            HTTP_IDEMPOTENCY_KEY="clave-repetida",
        )
    assert respuesta.status_code == 200
    assert respuesta.data["reutilizado"] is True
    assert Pago.objects.filter(reserva=reserva).count() == 1


def test_tarjeta_invalida_es_rechazada(cliente_autenticado, reserva):
    datos = dict(TARJETA_OK, numero_tarjeta="1234567812345678")
    respuesta = cliente_autenticado.post(
        f"/api/v1/reservations/{reserva.id}/payment",
        datos,
        format="json",
        HTTP_IDEMPOTENCY_KEY="clave-invalida",
    )
    assert respuesta.data["pago"]["estado"] == EstadoPago.RECHAZADO
    reserva.refresh_from_db()
    assert reserva.estado == EstadoReserva.PENDIENTE


def test_reserva_expirada_no_se_puede_pagar(cliente_autenticado, reserva):
    Reserva.objects.filter(pk=reserva.pk).update(
        expira_en=timezone.now() - timedelta(minutes=1)
    )
    respuesta = cliente_autenticado.post(
        f"/api/v1/reservations/{reserva.id}/payment",
        TARJETA_OK,
        format="json",
        HTTP_IDEMPOTENCY_KEY="clave-expirada",
    )
    assert respuesta.status_code == 410
    assert respuesta.data["error"]["codigo"] == "reserva_expirada"


def test_otro_usuario_no_puede_ver_el_ticket(api, cliente_autenticado, reserva, otro_usuario):
    cliente_autenticado.post(
        f"/api/v1/reservations/{reserva.id}/payment",
        TARJETA_OK,
        format="json",
        HTTP_IDEMPOTENCY_KEY="clave-ticket",
    )
    login = api.post(
        "/api/v1/auth/login",
        {"email": otro_usuario.email, "password": "Cine2026!"},
        format="json",
    )
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    assert api.get(f"/api/v1/reservations/{reserva.id}/ticket").status_code == 403
