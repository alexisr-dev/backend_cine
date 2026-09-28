from django_filters import rest_framework as filters

from .models import Pelicula


class PeliculaFilter(filters.FilterSet):
    genero = filters.CharFilter(field_name="generos__nombre", lookup_expr="iexact")
    genero_id = filters.NumberFilter(field_name="generos__id")
    clasificacion = filters.CharFilter(lookup_expr="iexact")
    estreno_desde = filters.DateFilter(field_name="fecha_estreno", lookup_expr="gte")
    estreno_hasta = filters.DateFilter(field_name="fecha_estreno", lookup_expr="lte")
    duracion_max = filters.NumberFilter(field_name="duracion_min", lookup_expr="lte")

    class Meta:
        model = Pelicula
        fields = ("genero", "genero_id", "clasificacion", "activa")
