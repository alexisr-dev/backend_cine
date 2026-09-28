import pytest

from apps.movies.models import Genero, Pelicula

pytestmark = pytest.mark.django_db


def test_anonimo_no_puede_listar_admin(api, pelicula):
    respuesta = api.get("/api/v1/admin/movies")
    assert respuesta.status_code == 401


def test_no_admin_no_puede_listar_admin(cliente_autenticado, pelicula):
    respuesta = cliente_autenticado.get("/api/v1/admin/movies")
    assert respuesta.status_code == 403


def test_admin_lista_incluye_inactivas(admin_autenticado, pelicula):
    pelicula.activa = False
    pelicula.save(update_fields=["activa"])
    Pelicula.objects.create(titulo="Otra pelicula", duracion_min=90)

    respuesta = admin_autenticado.get("/api/v1/admin/movies")
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 2


def test_admin_crea_pelicula_con_generos(admin_autenticado):
    accion = Genero.objects.create(nombre="Accion")
    drama = Genero.objects.create(nombre="Drama")

    respuesta = admin_autenticado.post(
        "/api/v1/admin/movies",
        {
            "titulo": "Estreno de prueba",
            "duracion_min": 120,
            "activa": True,
            "generos": [accion.id, drama.id],
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert {g["nombre"] for g in respuesta.data["generos"]} == {"Accion", "Drama"}

    creada = Pelicula.objects.get(titulo="Estreno de prueba")
    assert creada.generos.count() == 2


def test_creacion_rechaza_duracion_invalida(admin_autenticado):
    respuesta = admin_autenticado.post(
        "/api/v1/admin/movies",
        {"titulo": "Invalida", "duracion_min": 0, "activa": True},
        format="json",
    )
    assert respuesta.status_code == 400
    assert "duracion_min" in respuesta.data["error"]["detalles"]


def test_admin_actualiza_pelicula(admin_autenticado, api, pelicula):
    respuesta = admin_autenticado.put(
        f"/api/v1/admin/movies/{pelicula.id}",
        {
            "titulo": pelicula.titulo,
            "duracion_min": pelicula.duracion_min,
            "activa": False,
        },
        format="json",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["activa"] is False
    assert api.get("/api/v1/movies").data["count"] == 0


def test_admin_elimina_pelicula(admin_autenticado, pelicula):
    respuesta = admin_autenticado.delete(f"/api/v1/admin/movies/{pelicula.id}")
    assert respuesta.status_code == 204
    assert not Pelicula.objects.filter(id=pelicula.id).exists()


def test_admin_no_elimina_pelicula_con_funciones(admin_autenticado, funcion):
    respuesta = admin_autenticado.delete(f"/api/v1/admin/movies/{funcion.pelicula_id}")
    assert respuesta.status_code == 409
    assert Pelicula.objects.filter(id=funcion.pelicula_id).exists()
