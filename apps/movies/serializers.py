from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Genero, Pelicula


class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = ("id", "nombre")


class PeliculaListSerializer(serializers.ModelSerializer):
    generos = GeneroSerializer(many=True, read_only=True)
    duracion_legible = serializers.CharField(read_only=True)

    class Meta:
        model = Pelicula
        fields = (
            "id",
            "titulo",
            "titulo_original",
            "duracion_min",
            "duracion_legible",
            "clasificacion",
            "poster_url",
            "backdrop_url",
            "calificacion",
            "fecha_estreno",
            "generos",
        )


class PeliculaDetailSerializer(serializers.ModelSerializer):
    generos = GeneroSerializer(many=True, read_only=True)
    duracion_legible = serializers.CharField(read_only=True)
    reparto_lista = serializers.SerializerMethodField()

    class Meta:
        model = Pelicula
        fields = (
            "id",
            "titulo",
            "titulo_original",
            "sinopsis",
            "duracion_min",
            "duracion_legible",
            "clasificacion",
            "poster_url",
            "backdrop_url",
            "trailer_url",
            "idioma_original",
            "director",
            "reparto",
            "reparto_lista",
            "reparto_detalle",
            "calificacion",
            "fecha_estreno",
            "activa",
            "generos",
        )

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_reparto_lista(self, obj):
        if not obj.reparto:
            return []
        return [nombre.strip() for nombre in obj.reparto.split(",") if nombre.strip()]


class PeliculaWriteSerializer(serializers.ModelSerializer):
    generos = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Genero.objects.all(), required=False
    )

    class Meta:
        model = Pelicula
        fields = (
            "titulo",
            "titulo_original",
            "sinopsis",
            "duracion_min",
            "clasificacion",
            "poster_url",
            "backdrop_url",
            "trailer_url",
            "idioma_original",
            "director",
            "reparto",
            "calificacion",
            "fecha_estreno",
            "activa",
            "generos",
        )
