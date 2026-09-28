from django.db import models
from django.utils import timezone


class EstadoReserva(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de pago"
    CONFIRMADA = "confirmada", "Confirmada"
    CANCELADA = "cancelada", "Cancelada"
    EXPIRADA = "expirada", "Expirada"


class ReservaQuerySet(models.QuerySet):
    def completas(self):
        return self.select_related(
            "funcion",
            "funcion__pelicula",
            "funcion__sala",
            "funcion__sala__cine",
            "usuario",
        ).prefetch_related("asientos__funcion_asiento__asiento")

    def vivas(self):
        return self.filter(
            estado__in=[EstadoReserva.PENDIENTE, EstadoReserva.CONFIRMADA]
        )


class Reserva(models.Model):
    codigo_reserva = models.CharField(max_length=20, unique=True)
    usuario = models.ForeignKey(
        "users.Usuario",
        on_delete=models.PROTECT,
        related_name="reservas",
        db_column="usuario_id",
    )
    funcion = models.ForeignKey(
        "showtimes.Funcion",
        on_delete=models.PROTECT,
        related_name="reservas",
        db_column="funcion_id",
    )
    estado = models.CharField(
        max_length=20, choices=EstadoReserva.choices, default=EstadoReserva.PENDIENTE
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    expira_en = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ReservaQuerySet.as_manager()

    class Meta:
        db_table = "reservas"
        ordering = ["-created_at"]
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        indexes = [
            models.Index(fields=["usuario"], name="idx_reservas_usuario"),
            models.Index(fields=["funcion"], name="idx_reservas_funcion"),
            models.Index(fields=["estado"], name="idx_reservas_estado"),
        ]

    def __str__(self):
        return self.codigo_reserva

    @property
    def segundos_restantes(self):
        if self.estado != EstadoReserva.PENDIENTE:
            return 0
        delta = (self.expira_en - timezone.now()).total_seconds()
        return max(0, int(delta))

    @property
    def esta_vencida(self):
        return self.estado == EstadoReserva.PENDIENTE and self.expira_en < timezone.now()

    @property
    def cantidad_asientos(self):
        return self.asientos.count()


class ReservaAsiento(models.Model):
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE, related_name="asientos", db_column="reserva_id"
    )
    funcion_asiento = models.ForeignKey(
        "showtimes.FuncionAsiento",
        on_delete=models.PROTECT,
        related_name="reserva_asientos",
        db_column="funcion_asiento_id",
    )
    precio_pagado = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "reserva_asientos"
        ordering = ["funcion_asiento__asiento__fila", "funcion_asiento__asiento__numero"]
        verbose_name = "asiento reservado"
        verbose_name_plural = "asientos reservados"
        constraints = [
            models.UniqueConstraint(
                fields=["funcion_asiento"], name="uq_reserva_funcion_asiento"
            )
        ]

    def __str__(self):
        return f"{self.reserva.codigo_reserva} - {self.funcion_asiento.asiento}"
