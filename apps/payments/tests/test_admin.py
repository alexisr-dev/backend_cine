from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.payments.models import EstadoPago, Pago
from apps.reservations.models import Reserva

pytestmark = pytest.mark.django_db


@pytest.fixture
def reserva(usuario, funcion):
    return Reserva.objects.create(
        codigo_reserva="RSV-PAGO-1",
        usuario=usuario,
        funcion=funcion,
        total=Decimal("100.00"),
        expira_en=timezone.now() + timedelta(minutes=10),
    )


@pytest.fixture
def pago_aprobado(reserva):
    return Pago.objects.create(
        reserva=reserva,
        monto=reserva.total,
        estado=EstadoPago.APROBADO,
        idempotency_key="idem-admin-1",
    )


def test_anonimo_no_puede_listar_pagos(api, pago_aprobado):
    assert api.get("/api/v1/admin/payments").status_code == 401


def test_no_admin_no_puede_listar_pagos(cliente_autenticado, pago_aprobado):
    assert cliente_autenticado.get("/api/v1/admin/payments").status_code == 403


def test_admin_lista_pagos_con_datos_de_reserva(admin_autenticado, pago_aprobado):
    respuesta = admin_autenticado.get("/api/v1/admin/payments")
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    fila = respuesta.data["results"][0]
    assert fila["codigo_reserva"] == pago_aprobado.reserva.codigo_reserva
    assert fila["usuario_email"] == pago_aprobado.reserva.usuario.email


def test_admin_reembolsa_pago_aprobado(admin_autenticado, pago_aprobado):
    respuesta = admin_autenticado.post(f"/api/v1/admin/payments/{pago_aprobado.id}/refund")
    assert respuesta.status_code == 200
    pago_aprobado.refresh_from_db()
    assert pago_aprobado.estado == EstadoPago.REEMBOLSADO


def test_no_reembolsa_pago_no_aprobado(admin_autenticado, reserva):
    pago = Pago.objects.create(
        reserva=reserva,
        monto=reserva.total,
        estado=EstadoPago.RECHAZADO,
        idempotency_key="idem-admin-2",
    )
    respuesta = admin_autenticado.post(f"/api/v1/admin/payments/{pago.id}/refund")
    assert respuesta.status_code == 400
