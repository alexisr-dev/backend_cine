import secrets
import string

ALFABETO = string.ascii_uppercase + string.digits


def generar_codigo(prefijo="", longitud=8):
    cuerpo = "".join(secrets.choice(ALFABETO) for _ in range(longitud))
    return f"{prefijo}{cuerpo}" if prefijo else cuerpo


def generar_codigo_reserva():
    return generar_codigo(prefijo="CN-", longitud=8)


def generar_codigo_qr():
    return generar_codigo(longitud=24)
