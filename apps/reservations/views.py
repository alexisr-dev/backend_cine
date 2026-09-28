from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin, IsOwner

from .models import Reserva
from .serializers import (
    CrearReservaSerializer,
    ReservaAdminListSerializer,
    ReservaListSerializer,
    ReservaSerializer,
)
from .services import cancelar_reserva, crear_reserva, refrescar_estado


@extend_schema(request=CrearReservaSerializer, responses={201: ReservaSerializer})
class ReservaCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CrearReservaSerializer

    def post(self, request):
        serializer = CrearReservaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reserva = crear_reserva(
            usuario=request.user,
            funcion_id=serializer.validated_data["funcion_id"],
            funcion_asiento_ids=serializer.validated_data["funcion_asiento_ids"],
        )
        completa = Reserva.objects.completas().get(pk=reserva.pk)
        return Response(
            ReservaSerializer(completa).data, status=status.HTTP_201_CREATED
        )


class ReservaDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ReservaSerializer
    permission_classes = [IsAuthenticated, IsOwner]
    queryset = Reserva.objects.none()

    def get_queryset(self):
        return Reserva.objects.completas()

    def retrieve(self, request, *args, **kwargs):
        reserva = refrescar_estado(self.get_object())
        return Response(self.get_serializer(reserva).data)

    def destroy(self, request, *args, **kwargs):
        reserva = cancelar_reserva(self.get_object())
        return Response(
            ReservaSerializer(Reserva.objects.completas().get(pk=reserva.pk)).data
        )


@extend_schema(
    parameters=[
        OpenApiParameter(
            "estado", str, description="pendiente, confirmada, cancelada o expirada"
        )
    ]
)
class MisReservasView(generics.ListAPIView):
    serializer_class = ReservaListSerializer
    permission_classes = [IsAuthenticated]
    queryset = Reserva.objects.none()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Reserva.objects.none()
        queryset = Reserva.objects.filter(usuario=self.request.user).completas()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class AdminReservaListView(generics.ListAPIView):
    serializer_class = ReservaAdminListSerializer
    permission_classes = [IsAdmin]
    queryset = Reserva.objects.none()

    def get_queryset(self):
        queryset = Reserva.objects.completas()
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        usuario = self.request.query_params.get("usuario")
        if usuario:
            queryset = queryset.filter(usuario_id=usuario)
        return queryset
