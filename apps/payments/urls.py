from django.urls import path

from .views import (
    AdminPagoListView,
    AdminReembolsoView,
    PagosDeReservaView,
    ProcesarPagoView,
    TicketView,
)

urlpatterns = [
    path(
        "reservations/<int:pk>/payment",
        ProcesarPagoView.as_view(),
        name="reserva-pago",
    ),
    path(
        "reservations/<int:pk>/payments",
        PagosDeReservaView.as_view(),
        name="reserva-pagos",
    ),
    path("reservations/<int:pk>/ticket", TicketView.as_view(), name="reserva-ticket"),
    path("admin/payments", AdminPagoListView.as_view(), name="admin-pago-list"),
    path(
        "admin/payments/<int:pk>/refund",
        AdminReembolsoView.as_view(),
        name="admin-pago-refund",
    ),
]
