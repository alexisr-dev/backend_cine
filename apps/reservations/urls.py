from django.urls import path

from .views import (
    AdminReservaListView,
    MisReservasView,
    ReservaCreateView,
    ReservaDetailView,
)

urlpatterns = [
    path("reservations", ReservaCreateView.as_view(), name="reserva-create"),
    path("reservations/<int:pk>", ReservaDetailView.as_view(), name="reserva-detail"),
    path("users/me/reservations", MisReservasView.as_view(), name="reserva-mias"),
    path(
        "admin/reservations",
        AdminReservaListView.as_view(),
        name="admin-reserva-list",
    ),
]
