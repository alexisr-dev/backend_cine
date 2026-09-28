from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class DominioError(Exception):
    codigo = "error_dominio"
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detalle, codigo=None, status_code=None):
        super().__init__(detalle)
        self.detalle = detalle
        if codigo:
            self.codigo = codigo
        if status_code:
            self.status_code = status_code


class AsientoNoDisponible(DominioError):
    codigo = "asiento_no_disponible"
    status_code = status.HTTP_409_CONFLICT


class ReservaExpirada(DominioError):
    codigo = "reserva_expirada"
    status_code = status.HTTP_410_GONE


class OperacionInvalida(DominioError):
    codigo = "operacion_invalida"
    status_code = status.HTTP_400_BAD_REQUEST


def _formato(codigo, mensaje, detalles=None, request_id=None):
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje}}
    if detalles:
        cuerpo["error"]["detalles"] = detalles
    if request_id:
        cuerpo["error"]["request_id"] = request_id
    return cuerpo


def api_exception_handler(exc, context):
    request = context.get("request")
    request_id = getattr(request, "request_id", None)

    if isinstance(exc, DominioError):
        return Response(
            _formato(exc.codigo, exc.detalle, request_id=request_id),
            status=exc.status_code,
        )

    if isinstance(exc, DjangoValidationError):
        return Response(
            _formato("validacion", "Datos invalidos", exc.messages, request_id),
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, IntegrityError):
        return Response(
            _formato(
                "conflicto",
                "La operacion choca con el estado actual de los datos",
                request_id=request_id,
            ),
            status=status.HTTP_409_CONFLICT,
        )

    respuesta = exception_handler(exc, context)
    if respuesta is None:
        return None

    detalle = respuesta.data
    mensaje = "Solicitud invalida"
    detalles = None
    if isinstance(detalle, dict) and "detail" in detalle:
        mensaje = str(detalle["detail"])
    elif isinstance(detalle, dict):
        mensaje = "Datos invalidos"
        detalles = detalle
    elif isinstance(detalle, list):
        mensaje = "Datos invalidos"
        detalles = detalle

    respuesta.data = _formato(
        _codigo_por_status(respuesta.status_code), mensaje, detalles, request_id
    )
    return respuesta


def _codigo_por_status(codigo_http):
    return {
        400: "validacion",
        401: "no_autenticado",
        403: "sin_permiso",
        404: "no_encontrado",
        405: "metodo_no_permitido",
        409: "conflicto",
        429: "demasiadas_peticiones",
    }.get(codigo_http, "error")
