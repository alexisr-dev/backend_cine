import logging

from .services import expirar_reservas_vencidas

logger = logging.getLogger("cine.reservas")


def barrer_reservas_expiradas():
    liberados = expirar_reservas_vencidas()
    if liberados:
        logger.info("Holds vencidos liberados: %s", liberados)
    return liberados
