import threading
from datetime import timedelta

import pytest
from django.db import connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from apps.core.exceptions import AsientoNoDisponible, OperacionInvalida
from apps.movies.models import Pelicula
from apps.reservations.models import EstadoReserva, Reserva
from apps.reservations.services import cancelar_reserva, crear_reserva
from apps.showtimes.models import (
    Asiento,
    Cine,
    EstadoFuncionAsiento,
    Funcion,
    FuncionAsiento,
    Sala,
)
from apps.showtimes.services import generar_asientos_de_funcion


def _escenario():
    from django.contrib.auth import get_user_model

    Usuario = get_user_model()
    cine = Cine.objects.create(nombre="Cine Concurrencia", ciudad="CDMX")
    sala = Sala.objects.create(cine=cine, nombre="Sala 1", tipo_sala="2D", capacidad=10)
    Asiento.objects.bulk_create(
        [Asiento(sala=sala, fila="A", numero=numero) for numero in range(1, 11)]
    )
    pelicula = Pelicula.objects.create(titulo="Concurrencia", duracion_min=90)
    inicio = timezone.now() + timedelta(days=1)
    funcion = Funcion.objects.create(
        pelicula=pelicula,
        sala=sala,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=inicio + timedelta(minutes=110),
        precio_base=100,
    )
    generar_asientos_de_funcion(funcion)
    usuarios = [
        Usuario.objects.create_user(
            email=f"carrera{indice}@cine.mx",
            password="Cine2026!",
            nombre="Carrera",
            apellido=str(indice),
        )
        for indice in range(6)
    ]
    return funcion, usuarios


class ReservaConcurrenteTests(TransactionTestCase):
    reset_sequences = True

    def test_solo_una_reserva_gana_el_mismo_asiento(self):
        funcion, usuarios = _escenario()
        objetivo = FuncionAsiento.objects.filter(funcion=funcion).first()

        exitos = []
        fallos = []
        barrera = threading.Barrier(len(usuarios))

        def intentar(usuario):
            barrera.wait()
            try:
                with transaction.atomic():
                    crear_reserva(usuario, funcion.id, [objetivo.id])
                exitos.append(usuario.email)
            except (AsientoNoDisponible, OperacionInvalida) as error:
                fallos.append(str(error))
            finally:
                connections.close_all()

        hilos = [threading.Thread(target=intentar, args=(usuario,)) for usuario in usuarios]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(exitos) == 1
        assert len(fallos) == len(usuarios) - 1

        objetivo.refresh_from_db()
        assert objetivo.estado == EstadoFuncionAsiento.RESERVADO
        assert Reserva.objects.filter(estado=EstadoReserva.PENDIENTE).count() == 1

    def test_asientos_distintos_no_se_bloquean_entre_si(self):
        funcion, usuarios = _escenario()
        registros = list(FuncionAsiento.objects.filter(funcion=funcion)[:4])
        exitos = []
        barrera = threading.Barrier(len(registros))

        def intentar(usuario, registro):
            barrera.wait()
            try:
                with transaction.atomic():
                    crear_reserva(usuario, funcion.id, [registro.id])
                exitos.append(registro.id)
            finally:
                connections.close_all()

        hilos = [
            threading.Thread(target=intentar, args=(usuarios[indice], registro))
            for indice, registro in enumerate(registros)
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        assert len(exitos) == len(registros)


@pytest.mark.django_db
def test_reserva_marca_asientos_como_reservados(usuario, funcion):
    ids = list(FuncionAsiento.objects.filter(funcion=funcion).values_list("id", flat=True))[:3]
    reserva = crear_reserva(usuario, funcion.id, ids)

    assert reserva.estado == EstadoReserva.PENDIENTE
    assert reserva.total == sum(
        FuncionAsiento.objects.filter(id__in=ids).values_list("precio", flat=True)
    )
    assert (
        FuncionAsiento.objects.filter(
            id__in=ids, estado=EstadoFuncionAsiento.RESERVADO
        ).count()
        == 3
    )


@pytest.mark.django_db
def test_no_se_puede_reservar_un_asiento_ocupado(usuario, otro_usuario, funcion):
    registro = FuncionAsiento.objects.filter(funcion=funcion).first()
    crear_reserva(usuario, funcion.id, [registro.id])

    with pytest.raises(AsientoNoDisponible):
        crear_reserva(otro_usuario, funcion.id, [registro.id])


@pytest.mark.django_db
def test_hold_vencido_permite_reservar_de_nuevo(usuario, otro_usuario, funcion):
    registro = FuncionAsiento.objects.filter(funcion=funcion).first()
    primera = crear_reserva(usuario, funcion.id, [registro.id])

    Reserva.objects.filter(pk=primera.pk).update(
        expira_en=timezone.now() - timedelta(minutes=1)
    )
    FuncionAsiento.objects.filter(pk=registro.pk).update(
        reservado_hasta=timezone.now() - timedelta(minutes=1)
    )

    segunda = crear_reserva(otro_usuario, funcion.id, [registro.id])
    primera.refresh_from_db()

    assert primera.estado == EstadoReserva.EXPIRADA
    assert segunda.estado == EstadoReserva.PENDIENTE


@pytest.mark.django_db
def test_cancelar_libera_los_asientos(usuario, funcion):
    ids = list(FuncionAsiento.objects.filter(funcion=funcion).values_list("id", flat=True))[:2]
    reserva = crear_reserva(usuario, funcion.id, ids)
    cancelar_reserva(reserva)

    assert (
        FuncionAsiento.objects.filter(
            id__in=ids, estado=EstadoFuncionAsiento.DISPONIBLE
        ).count()
        == 2
    )
    reserva.refresh_from_db()
    assert reserva.estado == EstadoReserva.CANCELADA


@pytest.mark.django_db
def test_limite_de_asientos_por_reserva(usuario, funcion):
    ids = list(FuncionAsiento.objects.filter(funcion=funcion).values_list("id", flat=True))
    with pytest.raises(OperacionInvalida):
        crear_reserva(usuario, funcion.id, ids[:11])
