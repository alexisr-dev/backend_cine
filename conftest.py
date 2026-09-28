from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.movies.models import Pelicula
from apps.showtimes.models import Asiento, Cine, Funcion, Sala, TipoAsiento
from apps.showtimes.services import generar_asientos_de_funcion
from apps.users.models import RolUsuario

Usuario = get_user_model()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user(
        email="cliente@cine.mx", password="Cine2026!", nombre="Cliente", apellido="Uno"
    )


@pytest.fixture
def otro_usuario(db):
    return Usuario.objects.create_user(
        email="cliente2@cine.mx", password="Cine2026!", nombre="Cliente", apellido="Dos"
    )


@pytest.fixture
def pelicula(db):
    return Pelicula.objects.create(
        titulo="Pelicula de prueba", duracion_min=100, clasificacion="PG"
    )


@pytest.fixture
def sala(db):
    cine = Cine.objects.create(nombre="Cine Test", ciudad="CDMX")
    sala = Sala.objects.create(cine=cine, nombre="Sala 1", tipo_sala="2D", capacidad=20)
    Asiento.objects.bulk_create(
        [
            Asiento(sala=sala, fila=fila, numero=numero, tipo=TipoAsiento.ESTANDAR)
            for fila in ("A", "B")
            for numero in range(1, 11)
        ]
    )
    return sala


@pytest.fixture
def funcion(db, pelicula, sala):
    inicio = timezone.now() + timedelta(days=1)
    funcion = Funcion.objects.create(
        pelicula=pelicula,
        sala=sala,
        fecha_hora_inicio=inicio,
        fecha_hora_fin=inicio + timedelta(minutes=120),
        idioma="Espanol",
        precio_base=Decimal("100.00"),
    )
    generar_asientos_de_funcion(funcion)
    return funcion


@pytest.fixture
def cliente_autenticado(api, usuario):
    respuesta = api.post(
        "/api/v1/auth/login",
        {"email": usuario.email, "password": "Cine2026!"},
        format="json",
    )
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return api


@pytest.fixture
def usuario_admin(db):
    return Usuario.objects.create_user(
        email="admin@cine.mx",
        password="Cine2026!",
        nombre="Admin",
        apellido="Cine",
        rol=RolUsuario.ADMIN,
    )


@pytest.fixture
def admin_autenticado(api, usuario_admin):
    respuesta = api.post(
        "/api/v1/auth/login",
        {"email": usuario_admin.email, "password": "Cine2026!"},
        format="json",
    )
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return api
