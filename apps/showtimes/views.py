from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin

from .models import Cine, EstadoFuncionAsiento, Funcion, FuncionAsiento, Sala
from .serializers import (
    CineSerializer,
    FuncionCreateSerializer,
    FuncionDetailSerializer,
    FuncionListSerializer,
    FuncionUpdateSerializer,
    MapaAsientosSerializer,
    SalaSerializer,
    SalaWriteSerializer,
)
from .services import construir_mapa_asientos, resumen_disponibilidad


class CineListView(generics.ListAPIView):
    serializer_class = CineSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Cine.objects.all()


class AdminCineListCreateView(generics.ListCreateAPIView):
    serializer_class = CineSerializer
    permission_classes = [IsAdmin]
    pagination_class = None
    queryset = Cine.objects.all()


class AdminCineDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CineSerializer
    permission_classes = [IsAdmin]
    queryset = Cine.objects.all()


class AdminSalaListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]
    queryset = Sala.objects.select_related("cine").all()

    def get_serializer_class(self):
        return SalaWriteSerializer if self.request.method == "POST" else SalaSerializer

    def create(self, request, *args, **kwargs):
        entrada = SalaWriteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        sala = entrada.save()
        return Response(SalaSerializer(sala).data, status=status.HTTP_201_CREATED)


class AdminSalaDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Sala.objects.select_related("cine").all()

    def get_serializer_class(self):
        return SalaWriteSerializer if self.request.method in ("PUT", "PATCH") else SalaSerializer

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        entrada = SalaWriteSerializer(instancia, data=request.data, partial=parcial)
        entrada.is_valid(raise_exception=True)
        sala = entrada.save()
        return Response(SalaSerializer(sala).data)


class AdminFuncionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Funcion.objects.completas().order_by("-fecha_hora_inicio")
        params = self.request.query_params
        if params.get("pelicula"):
            queryset = queryset.filter(pelicula_id=params["pelicula"])
        if params.get("sala"):
            queryset = queryset.filter(sala_id=params["sala"])
        if params.get("activa") is not None:
            queryset = queryset.filter(activa=params["activa"].lower() == "true")
        return queryset

    def get_serializer_class(self):
        return FuncionCreateSerializer if self.request.method == "POST" else FuncionDetailSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        pagina = self.paginate_queryset(queryset)
        objetivo = pagina if pagina is not None else queryset
        disponibilidad = resumen_disponibilidad([f.id for f in objetivo])
        serializer = FuncionDetailSerializer(
            objetivo, many=True, context={"disponibilidad": disponibilidad}
        )
        if pagina is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        entrada = FuncionCreateSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        funcion = entrada.save()
        completa = Funcion.objects.completas().get(pk=funcion.pk)
        contexto = {"disponibilidad": resumen_disponibilidad([funcion.pk])}
        return Response(
            FuncionDetailSerializer(completa, context=contexto).data,
            status=status.HTTP_201_CREATED,
        )


class AdminFuncionDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdmin]
    queryset = Funcion.objects.completas()

    def get_serializer_class(self):
        return FuncionUpdateSerializer if self.request.method in ("PUT", "PATCH") else FuncionDetailSerializer

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["disponibilidad"] = resumen_disponibilidad([self.kwargs["pk"]])
        return contexto

    def update(self, request, *args, **kwargs):
        parcial = kwargs.pop("partial", False)
        instancia = self.get_object()
        entrada = FuncionUpdateSerializer(instancia, data=request.data, partial=parcial)
        entrada.is_valid(raise_exception=True)
        funcion = entrada.save()
        completa = Funcion.objects.completas().get(pk=funcion.pk)
        contexto = {"disponibilidad": resumen_disponibilidad([funcion.pk])}
        return Response(FuncionDetailSerializer(completa, context=contexto).data)


@extend_schema(
    parameters=[
        OpenApiParameter("fecha", str, description="Filtra por dia en formato AAAA-MM-DD"),
        OpenApiParameter("cine", int, description="Id del complejo"),
        OpenApiParameter("sala", int, description="Id de la sala"),
        OpenApiParameter("tipo_sala", str, description="2D, 3D, IMAX o 4DX"),
    ]
)
class FuncionListBase(generics.ListAPIView):
    serializer_class = FuncionListSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    queryset = Funcion.objects.none()

    def filtrar(self, queryset):
        params = self.request.query_params
        fecha = parse_date(params.get("fecha", "")) if params.get("fecha") else None
        if fecha:
            queryset = queryset.filter(fecha_hora_inicio__date=fecha)
        if params.get("cine"):
            queryset = queryset.filter(sala__cine_id=params["cine"])
        if params.get("sala"):
            queryset = queryset.filter(sala_id=params["sala"])
        if params.get("tipo_sala"):
            queryset = queryset.filter(sala__tipo_sala__iexact=params["tipo_sala"])
        return queryset

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["disponibilidad"] = getattr(self, "_disponibilidad", {})
        return contexto

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        self._disponibilidad = resumen_disponibilidad(
            list(queryset.values_list("id", flat=True))
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class FuncionListView(FuncionListBase):
    def get_queryset(self):
        queryset = Funcion.objects.activas().futuras().completas()
        return self.filtrar(queryset)


class FuncionesPorPeliculaView(FuncionListBase):
    def get_queryset(self):
        queryset = (
            Funcion.objects.activas()
            .futuras()
            .completas()
            .filter(pelicula_id=self.kwargs["pk"])
        )
        return self.filtrar(queryset)


class FuncionDetailView(generics.RetrieveAPIView):
    serializer_class = FuncionDetailSerializer
    permission_classes = [AllowAny]
    queryset = Funcion.objects.activas().completas()

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["disponibilidad"] = resumen_disponibilidad([self.kwargs["pk"]])
        return contexto


@extend_schema(responses={200: MapaAsientosSerializer})
class MapaAsientosView(APIView):
    permission_classes = [AllowAny]
    serializer_class = MapaAsientosSerializer

    def get(self, request, pk):
        funcion = get_object_or_404(Funcion.objects.completas(), pk=pk, activa=True)
        filas = construir_mapa_asientos(funcion)
        conteo = FuncionAsiento.objects.filter(funcion=funcion).aggregate(
            total=Count("id"),
            disponibles=Count("id", filter=Q(estado=EstadoFuncionAsiento.DISPONIBLE)),
            reservados=Count("id", filter=Q(estado=EstadoFuncionAsiento.RESERVADO)),
            ocupados=Count("id", filter=Q(estado=EstadoFuncionAsiento.OCUPADO)),
        )
        contexto = {"disponibilidad": {funcion.id: conteo}}
        return Response(
            {
                "funcion": FuncionDetailSerializer(funcion, context=contexto).data,
                "filas": filas,
                "resumen": conteo,
                "servidor_hora": timezone.now(),
            }
        )


@extend_schema(responses={200: serializers.ListSerializer(child=serializers.DateField())})
class FechasDisponiblesView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        fechas = (
            Funcion.objects.activas()
            .futuras()
            .filter(pelicula_id=pk)
            .dates("fecha_hora_inicio", "day")
        )
        return Response([fecha.isoformat() for fecha in fechas])
