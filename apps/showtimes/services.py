from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from .models import Asiento, EstadoFuncionAsiento, Funcion, FuncionAsiento, TipoAsiento

MULTIPLICADOR_PRECIO = {"estandar": 1.0, "vip": 1.5, "discapacitado": 1.0}


def generar_asientos_de_sala(sala, filas, por_fila):
    if sala.asientos.exists():
        return 0
    letras = [chr(ord("A") + indice) for indice in range(filas)]
    nuevos = []
    for indice, letra in enumerate(letras):
        for numero in range(1, por_fila + 1):
            if indice >= filas - 2:
                tipo = TipoAsiento.VIP
            elif indice == 0 and numero in (1, 2, por_fila - 1, por_fila):
                tipo = TipoAsiento.DISCAPACITADO
            else:
                tipo = TipoAsiento.ESTANDAR
            nuevos.append(Asiento(sala=sala, fila=letra, numero=numero, tipo=tipo))
    Asiento.objects.bulk_create(nuevos, batch_size=500)
    return len(nuevos)


@transaction.atomic
def liberar_holds_vencidos(funcion_id=None):
    from apps.reservations.models import EstadoReserva, Reserva, ReservaAsiento

    ahora = timezone.now()
    vencidos = FuncionAsiento.objects.filter(
        estado=EstadoFuncionAsiento.RESERVADO, reservado_hasta__lt=ahora
    )
    if funcion_id is not None:
        vencidos = vencidos.filter(funcion_id=funcion_id)

    ids = list(vencidos.values_list("id", flat=True))
    if not ids:
        return 0

    reservas_afectadas = list(
        Reserva.objects.filter(
            estado=EstadoReserva.PENDIENTE, asientos__funcion_asiento_id__in=ids
        )
        .distinct()
        .values_list("id", flat=True)
    )

    if reservas_afectadas:
        ReservaAsiento.objects.filter(reserva_id__in=reservas_afectadas).delete()
        Reserva.objects.filter(id__in=reservas_afectadas).update(
            estado=EstadoReserva.EXPIRADA, updated_at=ahora
        )

    FuncionAsiento.objects.filter(id__in=ids).update(
        estado=EstadoFuncionAsiento.DISPONIBLE,
        reservado_hasta=None,
        version=F("version") + 1,
    )
    return len(ids)


def construir_mapa_asientos(funcion):
    liberar_holds_vencidos(funcion.id)

    registros = (
        FuncionAsiento.objects.filter(funcion=funcion)
        .select_related("asiento")
        .order_by("asiento__fila", "asiento__numero")
    )

    filas = {}
    for registro in registros:
        asiento = registro.asiento
        filas.setdefault(asiento.fila, []).append(
            {
                "funcion_asiento_id": registro.id,
                "asiento_id": asiento.id,
                "fila": asiento.fila,
                "numero": asiento.numero,
                "etiqueta": asiento.etiqueta,
                "tipo": asiento.tipo,
                "estado": registro.estado,
                "precio": registro.precio,
                "activo": asiento.activo,
            }
        )

    return [
        {"fila": fila, "asientos": asientos}
        for fila, asientos in sorted(filas.items(), key=lambda item: item[0])
    ]


def resumen_disponibilidad(funcion_ids):
    ahora = timezone.now()
    agregados = (
        FuncionAsiento.objects.filter(funcion_id__in=funcion_ids)
        .values("funcion_id")
        .annotate(
            total=Count("id"),
            disponibles=Count(
                "id",
                filter=Q(estado=EstadoFuncionAsiento.DISPONIBLE)
                | Q(estado=EstadoFuncionAsiento.RESERVADO, reservado_hasta__lt=ahora),
            ),
        )
    )
    return {fila["funcion_id"]: fila for fila in agregados}


def generar_asientos_de_funcion(funcion: Funcion):
    existentes = set(
        FuncionAsiento.objects.filter(funcion=funcion).values_list("asiento_id", flat=True)
    )
    nuevos = [
        FuncionAsiento(
            funcion=funcion,
            asiento=asiento,
            precio=round(
                float(funcion.precio_base) * MULTIPLICADOR_PRECIO.get(asiento.tipo, 1.0), 2
            ),
        )
        for asiento in funcion.sala.asientos.filter(activo=True)
        if asiento.id not in existentes
    ]
    if nuevos:
        FuncionAsiento.objects.bulk_create(nuevos, batch_size=500)
    return len(nuevos)
