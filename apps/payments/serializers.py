from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import MetodoPago, Pago, Ticket


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = (
            "id",
            "reserva_id",
            "monto",
            "metodo_pago",
            "estado",
            "transaccion_externa_id",
            "tarjeta_ultimos4",
            "mensaje",
            "procesado_en",
            "created_at",
        )


class PagoAdminSerializer(PagoSerializer):
    codigo_reserva = serializers.CharField(source="reserva.codigo_reserva", read_only=True)
    usuario_email = serializers.EmailField(source="reserva.usuario.email", read_only=True)

    class Meta(PagoSerializer.Meta):
        fields = PagoSerializer.Meta.fields + ("codigo_reserva", "usuario_email")


class TicketSerializer(serializers.ModelSerializer):
    codigo_reserva = serializers.CharField(
        source="reserva.codigo_reserva", read_only=True
    )
    pelicula_titulo = serializers.CharField(
        source="reserva.funcion.pelicula.titulo", read_only=True
    )
    sala_nombre = serializers.CharField(source="reserva.funcion.sala.nombre", read_only=True)
    cine_nombre = serializers.CharField(
        source="reserva.funcion.sala.cine.nombre", read_only=True
    )
    fecha_hora_inicio = serializers.DateTimeField(
        source="reserva.funcion.fecha_hora_inicio", read_only=True
    )
    asientos = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = (
            "id",
            "codigo_qr",
            "emitido_en",
            "codigo_reserva",
            "pelicula_titulo",
            "sala_nombre",
            "cine_nombre",
            "fecha_hora_inicio",
            "asientos",
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_asientos(self, obj):
        return [
            item.funcion_asiento.asiento.etiqueta for item in obj.reserva.asientos.all()
        ]


class ProcesarPagoSerializer(serializers.Serializer):
    metodo_pago = serializers.ChoiceField(
        choices=MetodoPago.choices, default=MetodoPago.TARJETA
    )
    nombre_titular = serializers.CharField(max_length=120, required=False, allow_blank=True)
    numero_tarjeta = serializers.CharField(max_length=25, required=False, allow_blank=True)
    expiracion = serializers.CharField(max_length=7, required=False, allow_blank=True)
    cvv = serializers.CharField(max_length=4, required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get("metodo_pago", MetodoPago.TARJETA) == MetodoPago.TARJETA:
            faltantes = [
                campo
                for campo in ("nombre_titular", "numero_tarjeta", "expiracion", "cvv")
                if not attrs.get(campo)
            ]
            if faltantes:
                raise serializers.ValidationError(
                    {campo: "Este campo es obligatorio" for campo in faltantes}
                )
        return attrs
