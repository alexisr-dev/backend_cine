from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.showtimes.models import Asiento, Cine, Funcion, Sala

pytestmark = pytest.mark.django_db


def test_anonimo_no_puede_crear_cine(api):
    respuesta = api.post("/api/v1/admin/cinemas", {"nombre": "X"}, format="json")
    assert respuesta.status_code == 401


def test_no_admin_no_puede_crear_cine(cliente_autenticado):
    respuesta = cliente_autenticado.post(
        "/api/v1/admin/cinemas", {"nombre": "X"}, format="json"
    )
    assert respuesta.status_code == 403


def test_admin_crea_cine(admin_autenticado):
    respuesta = admin_autenticado.post(
        "/api/v1/admin/cinemas",
        {"nombre": "Cine Test", "ciudad": "CDMX"},
        format="json",
    )
    assert respuesta.status_code == 201
    assert Cine.objects.filter(nombre="Cine Test").exists()


def test_admin_crea_sala_genera_asientos(admin_autenticado):
    cine = Cine.objects.create(nombre="Cine Sala Test")
    respuesta = admin_autenticado.post(
        "/api/v1/admin/rooms",
        {"cine": cine.id, "nombre": "Sala 1", "tipo_sala": "2D", "filas": 4, "asientos_por_fila": 6},
        format="json",
    )
    assert respuesta.status_code == 201
    sala = Sala.objects.get(id=respuesta.data["id"])
    assert sala.capacidad == 24
    assert Asiento.objects.filter(sala=sala).count() == 24


def test_admin_crea_funcion_con_asientos(admin_autenticado, pelicula, sala):
    inicio = timezone.now() + timedelta(days=1)
    respuesta = admin_autenticado.post(
        "/api/v1/admin/showtimes",
        {
            "pelicula": pelicula.id,
            "sala": sala.id,
            "fecha_hora_inicio": inicio.isoformat(),
            "idioma": "Espanol",
            "subtitulos": False,
            "precio_base": "100.00",
            "activa": True,
        },
        format="json",
    )
    assert respuesta.status_code == 201
    funcion = Funcion.objects.get(id=respuesta.data["id"])
    assert funcion.funcion_asientos.count() == sala.asientos.filter(activo=True).count()
    assert respuesta.data["asientos_disponibles"] == respuesta.data["asientos_totales"]


def test_rechaza_funcion_muy_pronto(admin_autenticado, pelicula, sala):
    inicio = timezone.now() + timedelta(minutes=5)
    respuesta = admin_autenticado.post(
        "/api/v1/admin/showtimes",
        {
            "pelicula": pelicula.id,
            "sala": sala.id,
            "fecha_hora_inicio": inicio.isoformat(),
            "precio_base": "100.00",
        },
        format="json",
    )
    assert respuesta.status_code == 400


def test_rechaza_traslape_de_horario(admin_autenticado, pelicula, sala, funcion):
    inicio = funcion.fecha_hora_inicio + timedelta(minutes=10)
    respuesta = admin_autenticado.post(
        "/api/v1/admin/showtimes",
        {
            "pelicula": pelicula.id,
            "sala": sala.id,
            "fecha_hora_inicio": inicio.isoformat(),
            "precio_base": "100.00",
        },
        format="json",
    )
    assert respuesta.status_code == 400
    assert "fecha_hora_inicio" in respuesta.data["error"]["detalles"]


def test_admin_cancela_funcion_con_patch(admin_autenticado, funcion):
    respuesta = admin_autenticado.patch(
        f"/api/v1/admin/showtimes/{funcion.id}", {"activa": False}, format="json"
    )
    assert respuesta.status_code == 200
    assert respuesta.data["activa"] is False


def test_no_borra_funcion_con_reserva(admin_autenticado, funcion, usuario):
    from apps.reservations.models import Reserva

    Reserva.objects.create(
        codigo_reserva="RSV-TEST-1",
        usuario=usuario,
        funcion=funcion,
        total=Decimal("100.00"),
        expira_en=timezone.now() + timedelta(minutes=10),
    )
    respuesta = admin_autenticado.delete(f"/api/v1/admin/showtimes/{funcion.id}")
    assert respuesta.status_code == 409
    assert Funcion.objects.filter(id=funcion.id).exists()
