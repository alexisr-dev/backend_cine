import pytest

from apps.movies.models import Genero, PeliculaGenero

pytestmark = pytest.mark.django_db


def test_catalogo_lista_peliculas_activas(api, pelicula):
    respuesta = api.get("/api/v1/movies")
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1


def test_catalogo_oculta_peliculas_inactivas(api, pelicula):
    pelicula.activa = False
    pelicula.save(update_fields=["activa"])
    assert api.get("/api/v1/movies").data["count"] == 0


def test_filtro_por_genero(api, pelicula):
    genero = Genero.objects.create(nombre="Drama")
    PeliculaGenero.objects.create(pelicula=pelicula, genero=genero)
    assert api.get("/api/v1/movies?genero=Drama").data["count"] == 1
    assert api.get("/api/v1/movies?genero=Terror").data["count"] == 0


def test_busqueda_por_titulo(api, pelicula):
    assert api.get("/api/v1/movies?search=prueba").data["count"] == 1
    assert api.get("/api/v1/movies?search=inexistente").data["count"] == 0


def test_detalle_incluye_duracion_legible(api, pelicula):
    respuesta = api.get(f"/api/v1/movies/{pelicula.id}")
    assert respuesta.status_code == 200
    assert respuesta.data["duracion_legible"] == "1h 40m"
