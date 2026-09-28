from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.users.permissions import IsAdmin

from .filters import PeliculaFilter
from .models import Genero, Pelicula
from .serializers import (
    GeneroSerializer,
    PeliculaDetailSerializer,
    PeliculaListSerializer,
    PeliculaWriteSerializer,
)


class GeneroListView(generics.ListAPIView):
    serializer_class = GeneroSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Genero.objects.all()


class PeliculaListView(generics.ListAPIView):
    serializer_class = PeliculaListSerializer
    permission_classes = [AllowAny]
    filterset_class = PeliculaFilter
    search_fields = ("titulo", "titulo_original", "director", "reparto")
    ordering_fields = ("fecha_estreno", "titulo", "calificacion", "duracion_min")
    ordering = ("-fecha_estreno",)

    def get_queryset(self):
        return Pelicula.objects.activas().con_generos().distinct()


class PeliculaDetailView(generics.RetrieveAPIView):
    serializer_class = PeliculaDetailSerializer
    permission_classes = [AllowAny]
    queryset = Pelicula.objects.activas().con_generos()


class AdminPeliculaListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    filterset_class = PeliculaFilter
    search_fields = ("titulo", "titulo_original", "director", "reparto")
    ordering_fields = (
        "fecha_estreno",
        "titulo",
        "calificacion",
        "duracion_min",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def get_queryset(self):
        return Pelicula.objects.con_generos().distinct()

    def get_serializer_class(self):
        return PeliculaWriteSerializer if self.request.method == "POST" else PeliculaDetailSerializer

    def create(self, request, *args, **kwargs):
        entrada = PeliculaWriteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        pelicula = entrada.save()
        return Response(PeliculaDetailSerializer(pelicula).data, status=status.HTTP_201_CREATED)


class AdminPeliculaDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Pelicula.objects.con_generos()

    def get_serializer_class(self):
        return PeliculaWriteSerializer if self.request.method in ("PUT", "PATCH") else PeliculaDetailSerializer

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        entrada = PeliculaWriteSerializer(instancia, data=request.data, partial=parcial)
        entrada.is_valid(raise_exception=True)
        pelicula = entrada.save()
        return Response(PeliculaDetailSerializer(pelicula).data)
