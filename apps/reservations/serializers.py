from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.payments.serializers import PagoSerializer, TicketSerializer
from apps.showtimes.serializers import FuncionDetailSerializer

from .models import Reserva, ReservaAsiento


class ReservaAsientoSerializer(serializers.ModelSerializer):
    etiqueta = serializers.CharField(
        source="funcion_asiento.asiento.etiqueta", read_only=True
    )
    fila = serializers.CharField(source="funcion_asiento.asiento.fila", read_only=True)
    numero = serializers.IntegerField(
        source="funcion_asiento.asiento.numero", read_only=True
    )
    tipo = serializers.CharField(source="funcion_asiento.asiento.tipo", read_only=True)

    class Meta:
        model = ReservaAsiento
        fields = ("id", "funcion_asiento_id", "etiqueta", "fila", "numero", "tipo", "precio_pagado")


class ReservaSerializer(serializers.ModelSerializer):
    funcion = FuncionDetailSerializer(read_only=True)
    asientos = ReservaAsientoSerializer(many=True, read_only=True)
    segundos_restantes = serializers.IntegerField(read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)
    pago = serializers.SerializerMethodField()
    ticket = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = (
            "id",
            "codigo_reserva",
            "estado",
            "total",
            "expira_en",
            "segundos_restantes",
            "created_at",
            "usuario_email",
            "funcion",
            "asientos",
            "pago",
            "ticket",
        )

    @extend_schema_field(PagoSerializer(allow_null=True))
    def get_pago(self, obj):
        pago = obj.pagos.order_by("-created_at").first()
        if not pago:
            return None
        return {
            "id": pago.id,
            "estado": pago.estado,
            "monto": pago.monto,
            "metodo_pago": pago.metodo_pago,
            "transaccion_externa_id": pago.transaccion_externa_id,
            "procesado_en": pago.procesado_en,
        }

    @extend_schema_field(TicketSerializer(allow_null=True))
    def get_ticket(self, obj):
        ticket = getattr(obj, "ticket", None)
        if not ticket:
            return None
        return {"codigo_qr": ticket.codigo_qr, "emitido_en": ticket.emitido_en}


class ReservaListSerializer(serializers.ModelSerializer):
    pelicula_titulo = serializers.CharField(
        source="funcion.pelicula.titulo", read_only=True
    )
    poster_url = serializers.CharField(
        source="funcion.pelicula.poster_url", read_only=True
    )
    sala_nombre = serializers.CharField(source="funcion.sala.nombre", read_only=True)
    cine_nombre = serializers.CharField(source="funcion.sala.cine.nombre", read_only=True)
    fecha_hora_inicio = serializers.DateTimeField(
        source="funcion.fecha_hora_inicio", read_only=True
    )
    asientos = ReservaAsientoSerializer(many=True, read_only=True)
    segundos_restantes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Reserva
        fields = (
            "id",
            "codigo_reserva",
            "estado",
            "total",
            "expira_en",
            "segundos_restantes",
            "created_at",
            "pelicula_titulo",
            "poster_url",
            "sala_nombre",
            "cine_nombre",
            "fecha_hora_inicio",
            "asientos",
        )


class ReservaAdminListSerializer(ReservaListSerializer):
    usuario_id = serializers.IntegerField(source="usuario.id", read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    class Meta(ReservaListSerializer.Meta):
        fields = ReservaListSerializer.Meta.fields + ("usuario_id", "usuario_email")


class CrearReservaSerializer(serializers.Serializer):
    funcion_id = serializers.IntegerField()
    funcion_asiento_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, max_length=10
    )
