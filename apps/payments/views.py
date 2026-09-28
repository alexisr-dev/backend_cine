from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reservations.models import Reserva
from apps.reservations.serializers import ReservaSerializer
from apps.users.permissions import IsAdmin

from .models import Pago, Ticket
from .serializers import (
    PagoAdminSerializer,
    PagoSerializer,
    ProcesarPagoSerializer,
    TicketSerializer,
)
from .services import procesar_pago, reembolsar_pago


class RespuestaPagoSerializer(serializers.Serializer):
    pago = PagoSerializer()
    reserva = ReservaSerializer()
    reutilizado = serializers.BooleanField()


@extend_schema(
    request=ProcesarPagoSerializer,
    responses={200: RespuestaPagoSerializer, 201: RespuestaPagoSerializer},
    parameters=[
        OpenApiParameter(
            "Idempotency-Key",
            str,
            location=OpenApiParameter.HEADER,
            description="Evita cobrar dos veces si el request se reintenta",
        )
    ],
)
class ProcesarPagoView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProcesarPagoSerializer

    def post(self, request, pk):
        serializer = ProcesarPagoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pago, reutilizado = procesar_pago(
            reserva_id=pk,
            usuario=request.user,
            datos=serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"),
        )
        reserva = Reserva.objects.completas().get(pk=pago.reserva_id)
        codigo = status.HTTP_200_OK if reutilizado else status.HTTP_201_CREATED
        return Response(
            {
                "pago": PagoSerializer(pago).data,
                "reserva": ReservaSerializer(reserva).data,
                "reutilizado": reutilizado,
            },
            status=codigo,
        )


class TicketView(generics.RetrieveAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    queryset = Ticket.objects.none()

    def get_object(self):
        reserva = get_object_or_404(
            Reserva.objects.completas(), pk=self.kwargs["pk"]
        )
        if reserva.usuario_id != self.request.user.id and not self.request.user.es_admin:
            self.permission_denied(self.request, message="Esta reserva no te pertenece")
        return get_object_or_404(Ticket, reserva=reserva)


class PagosDeReservaView(generics.ListAPIView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    queryset = Pago.objects.none()

    def get_queryset(self):
        if "pk" not in self.kwargs:
            return Pago.objects.none()
        reserva = get_object_or_404(Reserva, pk=self.kwargs["pk"])
        if reserva.usuario_id != self.request.user.id and not self.request.user.es_admin:
            self.permission_denied(self.request, message="Esta reserva no te pertenece")
        return reserva.pagos.all()


class AdminPagoListView(generics.ListAPIView):
    serializer_class = PagoAdminSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Pago.objects.select_related("reserva", "reserva__usuario").order_by(
            "-created_at"
        )
        estado = self.request.query_params.get("estado")
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset


class AdminReembolsoView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        pago = get_object_or_404(Pago, pk=pk)
        pago = reembolsar_pago(pago)
        return Response(PagoAdminSerializer(pago).data)
