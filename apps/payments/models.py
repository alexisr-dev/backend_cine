from django.db import models


class EstadoPago(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    APROBADO = "aprobado", "Aprobado"
    RECHAZADO = "rechazado", "Rechazado"
    REEMBOLSADO = "reembolsado", "Reembolsado"


class MetodoPago(models.TextChoices):
    TARJETA = "tarjeta", "Tarjeta"
    STRIPE = "stripe", "Stripe"
    PAYPAL = "paypal", "PayPal"
    EFECTIVO = "efectivo", "Efectivo en taquilla"


class Pago(models.Model):
    reserva = models.ForeignKey(
        "reservations.Reserva",
        on_delete=models.PROTECT,
        related_name="pagos",
        db_column="reserva_id",
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(
        max_length=30, choices=MetodoPago.choices, default=MetodoPago.TARJETA
    )
    estado = models.CharField(
        max_length=20, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE
    )
    idempotency_key = models.CharField(max_length=100, unique=True)
    transaccion_externa_id = models.CharField(max_length=150, blank=True, null=True)
    tarjeta_ultimos4 = models.CharField(max_length=4, blank=True, null=True)
    mensaje = models.CharField(max_length=200, blank=True, null=True)
    procesado_en = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pagos"
        ordering = ["-created_at"]
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        indexes = [
            models.Index(fields=["idempotency_key"], name="idx_pagos_idempotency"),
            models.Index(fields=["reserva"], name="idx_pagos_reserva"),
        ]

    def __str__(self):
        return f"{self.reserva_id} - {self.estado} - {self.monto}"


class Ticket(models.Model):
    reserva = models.OneToOneField(
        "reservations.Reserva",
        on_delete=models.CASCADE,
        related_name="ticket",
        db_column="reserva_id",
    )
    codigo_qr = models.CharField(max_length=255, unique=True)
    emitido_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tickets"
        ordering = ["-emitido_en"]
        verbose_name = "ticket"
        verbose_name_plural = "tickets"

    def __str__(self):
        return self.codigo_qr
