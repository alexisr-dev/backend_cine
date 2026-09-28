from datetime import timedelta

import pytest
from django.utils import timezone

from apps.showtimes.models import EstadoFuncionAsiento, FuncionAsiento
from apps.showtimes.services import liberar_holds_vencidos

pytestmark = pytest.mark.django_db


def test_mapa_devuelve_todas_las_filas(api, funcion):
    respuesta = api.get(f"/api/v1/showtimes/{funcion.id}/seats")
    assert respuesta.status_code == 200
    assert len(respuesta.data["filas"]) == 2
    assert respuesta.data["resumen"]["total"] == 20
    assert respuesta.data["resumen"]["disponibles"] == 20


def test_precio_vip_supera_al_estandar(funcion, sala):
    asiento = sala.asientos.first()
    asiento.tipo = "vip"
    asiento.save(update_fields=["tipo"])
    FuncionAsiento.objects.filter(funcion=funcion).delete()
    from apps.showtimes.services import generar_asientos_de_funcion

    generar_asientos_de_funcion(funcion)
    vip = FuncionAsiento.objects.get(funcion=funcion, asiento=asiento)
    estandar = FuncionAsiento.objects.filter(funcion=funcion).exclude(id=vip.id).first()
    assert vip.precio > estandar.precio


def test_hold_vencido_se_libera(funcion):
    registro = FuncionAsiento.objects.filter(funcion=funcion).first()
    registro.estado = EstadoFuncionAsiento.RESERVADO
    registro.reservado_hasta = timezone.now() - timedelta(minutes=1)
    registro.save(update_fields=["estado", "reservado_hasta"])

    assert liberar_holds_vencidos(funcion.id) == 1
    registro.refresh_from_db()
    assert registro.estado == EstadoFuncionAsiento.DISPONIBLE
    assert registro.reservado_hasta is None


def test_funciones_pasadas_no_se_listan(api, funcion):
    funcion.fecha_hora_inicio = timezone.now() - timedelta(hours=3)
    funcion.fecha_hora_fin = timezone.now() - timedelta(hours=1)
    funcion.save(update_fields=["fecha_hora_inicio", "fecha_hora_fin"])
    respuesta = api.get(f"/api/v1/movies/{funcion.pelicula_id}/showtimes")
    assert respuesta.data == []
