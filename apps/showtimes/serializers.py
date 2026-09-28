from datetime import timedelta

from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.movies.models import Pelicula
from apps.movies.serializers import PeliculaListSerializer

from .models import Asiento, Cine, Funcion, FuncionAsiento, Sala
from .services import generar_asientos_de_funcion, generar_asientos_de_sala


class CineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cine
        fields = ("id", "nombre", "direccion", "ciudad", "telefono")


class SalaSerializer(serializers.ModelSerializer):
    cine = CineSerializer(read_only=True)

    class Meta:
        model = Sala
        fields = ("id", "nombre", "tipo_sala", "capacidad", "activa", "cine")


class SalaWriteSerializer(serializers.ModelSerializer):
    cine = serializers.PrimaryKeyRelatedField(queryset=Cine.objects.all())
    filas = serializers.IntegerField(write_only=True, min_value=1, max_value=26, required=False)
    asientos_por_fila = serializers.IntegerField(write_only=True, min_value=1, max_value=40, required=False)

    class Meta:
        model = Sala
        fields = ("id", "cine", "nombre", "tipo_sala", "activa", "filas", "asientos_por_fila")

    def create(self, validated_data):
        filas = validated_data.pop("filas", None)
        por_fila = validated_data.pop("asientos_por_fila", None)
        if not filas or not por_fila:
            raise serializers.ValidationError(
                {"filas": "Se requieren 'filas' y 'asientos_por_fila' para crear una sala"}
            )
        validated_data["capacidad"] = filas * por_fila
        sala = super().create(validated_data)
        generar_asientos_de_sala(sala, filas, por_fila)
        return sala

    def update(self, instance, validated_data):
        validated_data.pop("filas", None)
        validated_data.pop("asientos_por_fila", None)
        return super().update(instance, validated_data)


class AsientoSerializer(serializers.ModelSerializer):
    etiqueta = serializers.CharField(read_only=True)

    class Meta:
        model = Asiento
        fields = ("id", "fila", "numero", "etiqueta", "tipo", "activo")


class FuncionListSerializer(serializers.ModelSerializer):
    sala = SalaSerializer(read_only=True)
    pelicula_id = serializers.IntegerField(read_only=True)
    pelicula_titulo = serializers.CharField(source="pelicula.titulo", read_only=True)
    pelicula_poster_url = serializers.CharField(source="pelicula.poster_url", read_only=True)
    asientos_disponibles = serializers.SerializerMethodField()
    asientos_totales = serializers.SerializerMethodField()

    class Meta:
        model = Funcion
        fields = (
            "id",
            "pelicula_id",
            "pelicula_titulo",
            "pelicula_poster_url",
            "sala",
            "fecha_hora_inicio",
            "fecha_hora_fin",
            "idioma",
            "subtitulos",
            "precio_base",
            "activa",
            "asientos_disponibles",
            "asientos_totales",
        )

    def _resumen(self, obj):
        return self.context.get("disponibilidad", {}).get(obj.id, {})

    @extend_schema_field(serializers.IntegerField())
    def get_asientos_disponibles(self, obj):
        return self._resumen(obj).get("disponibles", 0)

    @extend_schema_field(serializers.IntegerField())
    def get_asientos_totales(self, obj):
        return self._resumen(obj).get("total", obj.sala.capacidad)


class FuncionDetailSerializer(FuncionListSerializer):
    pelicula = PeliculaListSerializer(read_only=True)

    class Meta(FuncionListSerializer.Meta):
        fields = FuncionListSerializer.Meta.fields + ("pelicula",)


def _validar_horario_funcion(attrs, instance):
    pelicula = attrs.get("pelicula") or (instance.pelicula if instance else None)
    sala = attrs.get("sala") or (instance.sala if instance else None)
    inicio = attrs.get("fecha_hora_inicio") or (instance.fecha_hora_inicio if instance else None)

    if inicio and inicio <= timezone.now() + timedelta(minutes=30):
        raise serializers.ValidationError(
            {"fecha_hora_inicio": "Debe programarse con al menos 30 minutos de anticipacion"}
        )

    fin = inicio + timedelta(minutes=pelicula.duracion_min + 20)

    traslape = Funcion.objects.filter(
        sala=sala, fecha_hora_inicio__lt=fin, fecha_hora_fin__gt=inicio
    )
    if instance:
        traslape = traslape.exclude(pk=instance.pk)
    if traslape.exists():
        raise serializers.ValidationError(
            {"fecha_hora_inicio": "Ya hay otra funcion programada en esa sala en ese horario"}
        )

    attrs["fecha_hora_fin"] = fin
    return attrs


class FuncionCreateSerializer(serializers.ModelSerializer):
    pelicula = serializers.PrimaryKeyRelatedField(queryset=Pelicula.objects.all())
    sala = serializers.PrimaryKeyRelatedField(queryset=Sala.objects.all())

    class Meta:
        model = Funcion
        fields = (
            "id",
            "pelicula",
            "sala",
            "fecha_hora_inicio",
            "idioma",
            "subtitulos",
            "precio_base",
            "activa",
        )

    def validate(self, attrs):
        return _validar_horario_funcion(attrs, instance=None)

    def create(self, validated_data):
        funcion = super().create(validated_data)
        generar_asientos_de_funcion(funcion)
        return funcion


class FuncionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcion
        fields = ("id", "fecha_hora_inicio", "idioma", "subtitulos", "precio_base", "activa")

    def validate(self, attrs):
        return _validar_horario_funcion(attrs, instance=self.instance)


class MapaAsientoSerializer(serializers.Serializer):
    funcion_asiento_id = serializers.IntegerField()
    asiento_id = serializers.IntegerField()
    fila = serializers.CharField()
    numero = serializers.IntegerField()
    etiqueta = serializers.CharField()
    tipo = serializers.CharField()
    estado = serializers.CharField()
    precio = serializers.DecimalField(max_digits=10, decimal_places=2)
    activo = serializers.BooleanField()


class MapaFilaSerializer(serializers.Serializer):
    fila = serializers.CharField()
    asientos = MapaAsientoSerializer(many=True)


class MapaAsientosSerializer(serializers.Serializer):
    funcion = FuncionDetailSerializer()
    filas = MapaFilaSerializer(many=True)
    resumen = serializers.DictField()


class FuncionAsientoSerializer(serializers.ModelSerializer):
    asiento = AsientoSerializer(read_only=True)

    class Meta:
        model = FuncionAsiento
        fields = ("id", "funcion_id", "asiento", "precio", "estado", "reservado_hasta")
