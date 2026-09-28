import hashlib
import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.core.exceptions import OperacionInvalida, ReservaExpirada
from apps.core.utils import generar_codigo_qr
from apps.reservations.models import EstadoReserva, Reserva
from apps.reservations.services import confirmar_reserva

from .models import EstadoPago, Pago, Ticket

TARJETAS_RECHAZADAS = {"4000000000000002", "4000000000009995"}


def _solo_digitos(valor):
    return "".join(caracter for caracter in (valor or "") if caracter.isdigit())


def _luhn_valido(numero):
    digitos = [int(caracter) for caracter in numero][::-1]
    suma = 0
    for indice, digito in enumerate(digitos):
        if indice % 2 == 1:
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito
    return suma % 10 == 0


def _clave_idempotencia(reserva, entrante):
    if entrante:
        return entrante[:100]
    semilla = f"{reserva.id}:{reserva.codigo_reserva}:{uuid.uuid4()}"
    return hashlib.sha256(semilla.encode()).hexdigest()[:64]


def _autorizar(numero_tarjeta):
    numero = _solo_digitos(numero_tarjeta)
    if len(numero) < 13 or len(numero) > 19:
        return False, "El numero de tarjeta no es valido"
    if not _luhn_valido(numero):
        return False, "El numero de tarjeta no paso la verificacion"
    if numero in TARJETAS_RECHAZADAS:
        return False, "El emisor rechazo el cargo"
    return True, "Pago aprobado"


@transaction.atomic
def procesar_pago(reserva_id, usuario, datos, idempotency_key=None):
    try:
        reserva = Reserva.objects.select_for_update().get(pk=reserva_id)
    except Reserva.DoesNotExist:
        raise OperacionInvalida("La reserva no existe")

    if reserva.usuario_id != usuario.id and not usuario.es_admin:
        raise OperacionInvalida("Esta reserva no te pertenece")

    if idempotency_key:
        existente = Pago.objects.filter(idempotency_key=idempotency_key).first()
        if existente:
            if existente.reserva_id != reserva.id:
                raise OperacionInvalida(
                    "La clave de idempotencia ya se uso en otra reserva"
                )
            return existente, True

    if reserva.estado == EstadoReserva.CONFIRMADA:
        pago_previo = reserva.pagos.filter(estado=EstadoPago.APROBADO).first()
        if pago_previo:
            return pago_previo, True
    if reserva.estado in (EstadoReserva.CANCELADA, EstadoReserva.EXPIRADA):
        raise ReservaExpirada("La reserva ya no esta activa")
    if reserva.expira_en < timezone.now():
        raise ReservaExpirada("La reserva expiro, vuelve a elegir tus asientos")

    clave = _clave_idempotencia(reserva, idempotency_key)
    numero_tarjeta = _solo_digitos(datos.get("numero_tarjeta"))
    metodo = datos.get("metodo_pago") or "tarjeta"

    aprobado, mensaje = (
        _autorizar(numero_tarjeta) if metodo == "tarjeta" else (True, "Pago aprobado")
    )

    try:
        pago = Pago.objects.create(
            reserva=reserva,
            monto=Decimal(reserva.total),
            metodo_pago=metodo,
            estado=EstadoPago.APROBADO if aprobado else EstadoPago.RECHAZADO,
            idempotency_key=clave,
            transaccion_externa_id=f"tx_{uuid.uuid4().hex[:20]}" if aprobado else None,
            tarjeta_ultimos4=numero_tarjeta[-4:] if numero_tarjeta else None,
            mensaje=mensaje,
            procesado_en=timezone.now(),
        )
    except IntegrityError:
        pago = Pago.objects.get(idempotency_key=clave)
        return pago, True

    if aprobado:
        confirmar_reserva(reserva)
        Ticket.objects.get_or_create(
            reserva=reserva, defaults={"codigo_qr": generar_codigo_qr()}
        )

    return pago, False


def reembolsar_pago(pago):
    if pago.estado != EstadoPago.APROBADO:
        raise OperacionInvalida("Solo se pueden reembolsar pagos aprobados")
    pago.estado = EstadoPago.REEMBOLSADO
    pago.mensaje = "Reembolso emitido"
    pago.save(update_fields=["estado", "mensaje"])
    return pago
