from django.urls import path

from .views import (
    AdminCineDetailView,
    AdminCineListCreateView,
    AdminFuncionDetailView,
    AdminFuncionListCreateView,
    AdminSalaDetailView,
    AdminSalaListCreateView,
    CineListView,
    FechasDisponiblesView,
    FuncionDetailView,
    FuncionListView,
    FuncionesPorPeliculaView,
    MapaAsientosView,
)

urlpatterns = [
    path("cinemas", CineListView.as_view(), name="cine-list"),
    path("showtimes", FuncionListView.as_view(), name="funcion-list"),
    path("showtimes/<int:pk>", FuncionDetailView.as_view(), name="funcion-detail"),
    path("showtimes/<int:pk>/seats", MapaAsientosView.as_view(), name="funcion-seats"),
    path(
        "movies/<int:pk>/showtimes",
        FuncionesPorPeliculaView.as_view(),
        name="pelicula-showtimes",
    ),
    path(
        "movies/<int:pk>/showtime-dates",
        FechasDisponiblesView.as_view(),
        name="pelicula-showtime-dates",
    ),
    path(
        "admin/cinemas",
        AdminCineListCreateView.as_view(),
        name="admin-cine-list-create",
    ),
    path("admin/cinemas/<int:pk>", AdminCineDetailView.as_view(), name="admin-cine-detail"),
    path(
        "admin/rooms",
        AdminSalaListCreateView.as_view(),
        name="admin-sala-list-create",
    ),
    path("admin/rooms/<int:pk>", AdminSalaDetailView.as_view(), name="admin-sala-detail"),
    path(
        "admin/showtimes",
        AdminFuncionListCreateView.as_view(),
        name="admin-funcion-list-create",
    ),
    path(
        "admin/showtimes/<int:pk>",
        AdminFuncionDetailView.as_view(),
        name="admin-funcion-detail",
    ),
]
