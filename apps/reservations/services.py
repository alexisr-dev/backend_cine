from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.core.exceptions import AsientoNoDisponible, OperacionInvalida, ReservaExpirada
from apps.core.utils import generar_codigo_reserva
from apps.showtimes.models import EstadoFuncionAsiento, Funcion, FuncionAsiento
from apps.showtimes.services import liberar_holds_vencidos

from .models import EstadoReserva, Reserva, ReservaAsiento

MAX_ASIENTOS_POR_RESERVA = 10


def _minutos_hold():
    return getattr(settings, "HOLD_MINUTOS", 10)


@transaction.atomic
def crear_reserva(usuario, funcion_id, funcion_asiento_ids):
    ids = list(dict.fromkeys(int(valor) for valor in funcion_asiento_ids))
    if not ids:
        raise OperacionInvalida("Selecciona al menos un asiento")
    if len(ids) > MAX_ASIENTOS_POR_RESERVA:
        raise OperacionInvalida(
            f"Puedes reservar hasta {MAX_ASIENTOS_POR_RESERVA} asientos por operacion"
        )

    try:
        funcion = Funcion.objects.select_related("sala", "pelicula").get(
            pk=funcion_id, activa=True
        )
    except Funcion.DoesNotExist:
        raise OperacionInvalida("La funcion no existe o no esta disponible")

    if funcion.fecha_hora_inicio <= timezone.now():
        raise OperacionInvalida("La funcion ya comenzo")

    liberar_holds_vencidos(funcion.id)

    ahora = timezone.now()
    bloqueados = list(
        FuncionAsiento.objects.select_for_update()
        .select_related("asiento")
        .filter(id__in=ids, funcion_id=funcion.id)
        .order_by("id")
    )

    if len(bloqueados) != len(ids):
        raise OperacionInvalida("Algunos asientos no pertenecen a esta funcion")

    no_disponibles = []
    for registro in bloqueados:
        libre = registro.estado == EstadoFuncionAsiento.DISPONIBLE or (
            registro.estado == EstadoFuncionAsiento.RESERVADO
            and registro.reservado_hasta is not None
            and registro.reservado_hasta < ahora
        )
        if not registro.asiento.activo or not libre:
            no_disponibles.append(registro.asiento.etiqueta)

    if no_disponibles:
        raise AsientoNoDisponible(
            f"Estos asientos ya fueron tomados: {', '.join(sorted(no_disponibles))}"
        )

    ReservaAsiento.objects.filter(
        funcion_asiento_id__in=ids,
        reserva__estado__in=[EstadoReserva.PENDIENTE, EstadoReserva.EXPIRADA],
    ).delete()

    expira_en = ahora + timedelta(minutes=_minutos_hold())
    total = sum((registro.precio for registro in bloqueados), Decimal("0.00"))

    reserva = Reserva.objects.create(
        codigo_reserva=generar_codigo_reserva(),
        usuario=usuario,
        funcion=funcion,
        estado=EstadoReserva.PENDIENTE,
        total=total,
        expira_en=expira_en,
    )

    try:
        ReservaAsiento.objects.bulk_create(
            [
                ReservaAsiento(
                    reserva=reserva,
                    funcion_asiento=registro,
                    precio_pagado=registro.precio,
                )
                for registro in bloqueados
            ]
        )
    except IntegrityError:
        raise AsientoNoDisponible("Otro usuario reservo estos asientos primero")

    FuncionAsiento.objects.filter(id__in=ids).update(
        estado=EstadoFuncionAsiento.RESERVADO,
        reservado_hasta=expira_en,
        version=F("version") + 1,
    )

    return reserva


@transaction.atomic
def cancelar_reserva(reserva):
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado in (EstadoReserva.CANCELADA, EstadoReserva.EXPIRADA):
        return reserva
    if reserva.estado == EstadoReserva.CONFIRMADA:
        if reserva.funcion.fecha_hora_inicio - timezone.now() < timedelta(hours=1):
            raise OperacionInvalida(
                "No se puede cancelar a menos de una hora del inicio de la funcion"
            )

    ids = list(reserva.asientos.values_list("funcion_asiento_id", flat=True))
    reserva.asientos.all().delete()
    FuncionAsiento.objects.filter(id__in=ids).update(
        estado=EstadoFuncionAsiento.DISPONIBLE,
        reservado_hasta=None,
        version=F("version") + 1,
    )
    reserva.estado = EstadoReserva.CANCELADA
    reserva.save(update_fields=["estado", "updated_at"])
    return reserva


@transaction.atomic
def confirmar_reserva(reserva):
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado == EstadoReserva.CONFIRMADA:
        return reserva
    if reserva.estado != EstadoReserva.PENDIENTE:
        raise OperacionInvalida("La reserva no esta pendiente de pago")
    if reserva.expira_en < timezone.now():
        raise ReservaExpirada("La reserva expiro, vuelve a elegir tus asientos")

    ids = list(reserva.asientos.values_list("funcion_asiento_id", flat=True))
    FuncionAsiento.objects.filter(id__in=ids).update(
        estado=EstadoFuncionAsiento.OCUPADO,
        reservado_hasta=None,
        version=F("version") + 1,
    )
    reserva.estado = EstadoReserva.CONFIRMADA
    reserva.save(update_fields=["estado", "updated_at"])
    return reserva


def expirar_reservas_vencidas():
    return liberar_holds_vencidos()


def refrescar_estado(reserva):
    if reserva.esta_vencida:
        liberar_holds_vencidos(reserva.funcion_id)
        reserva.refresh_from_db()
    return reserva
