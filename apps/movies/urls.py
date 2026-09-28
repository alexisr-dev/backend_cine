from django.urls import path

from .views import (
    AdminPeliculaDetailView,
    AdminPeliculaListCreateView,
    GeneroListView,
    PeliculaDetailView,
    PeliculaListView,
)

urlpatterns = [
    path("genres", GeneroListView.as_view(), name="genero-list"),
    path("movies", PeliculaListView.as_view(), name="pelicula-list"),
    path("movies/<int:pk>", PeliculaDetailView.as_view(), name="pelicula-detail"),
    path(
        "admin/movies",
        AdminPeliculaListCreateView.as_view(),
        name="admin-pelicula-list-create",
    ),
    path(
        "admin/movies/<int:pk>",
        AdminPeliculaDetailView.as_view(),
        name="admin-pelicula-detail",
    ),
]
