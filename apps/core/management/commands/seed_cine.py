import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.movies.models import Genero, Pelicula, PeliculaGenero
from apps.showtimes.models import Asiento, Cine, Funcion, Sala, TipoAsiento
from apps.showtimes.services import generar_asientos_de_funcion

Usuario = get_user_model()

GENEROS = [
    "Accion",
    "Aventura",
    "Animacion",
    "Ciencia ficcion",
    "Comedia",
    "Documental",
    "Drama",
    "Fantasia",
    "Suspenso",
    "Terror",
]

PELICULAS = [
    {
        "titulo": "Ultima Proyeccion",
        "titulo_original": "The Last Reel",
        "sinopsis": "El proyeccionista de un cine de barrio descubre que la pelicula que "
        "exhibe cada noche cambia de final segun quien la mire. Cuando la sala anuncia su "
        "cierre, decide averiguar quien escribe esos finales.",
        "duracion_min": 128,
        "clasificacion": "PG-13",
        "idioma_original": "Espanol",
        "director": "Irene Sandoval",
        "reparto": "Marta Belmonte, Julian Reyes, Ana Cortes, Diego Munoz",
        "calificacion": Decimal("8.4"),
        "fecha_estreno": date(2026, 6, 12),
        "generos": ["Drama", "Fantasia"],
    },
    {
        "titulo": "Orbita Cero",
        "titulo_original": "Zero Orbit",
        "sinopsis": "Una ingeniera queda varada en una estacion orbital abandonada con "
        "seis horas de oxigeno y una sola forma de volver: reiniciar un motor que nadie "
        "ha encendido en veinte anos.",
        "duracion_min": 141,
        "clasificacion": "PG-13",
        "idioma_original": "Ingles",
        "director": "Noor Haddad",
        "reparto": "Kaya Lindqvist, Samuel Otieno, Rin Nakamura",
        "calificacion": Decimal("8.9"),
        "fecha_estreno": date(2026, 7, 3),
        "generos": ["Ciencia ficcion", "Suspenso"],
    },
    {
        "titulo": "El Ruido del Bosque",
        "titulo_original": "What the Forest Keeps",
        "sinopsis": "Tres hermanos regresan a la cabana donde crecieron para vaciarla. "
        "El bosque los recibe con un sonido que solo ellos recuerdan, y que ninguno "
        "quiere nombrar.",
        "duracion_min": 106,
        "clasificacion": "R",
        "idioma_original": "Ingles",
        "director": "Tomas Vieira",
        "reparto": "Elsa Brandt, Paulo Vieira, Nadia Kern",
        "calificacion": Decimal("7.6"),
        "fecha_estreno": date(2026, 5, 29),
        "generos": ["Terror", "Suspenso"],
    },
    {
        "titulo": "Cumbia para Marte",
        "titulo_original": "Cumbia for Mars",
        "sinopsis": "Una banda de barrio gana por error un concurso para tocar en la "
        "primera colonia marciana. Tienen ocho meses para aprender a sobrevivir sin "
        "gravedad y sin pelearse entre ellos.",
        "duracion_min": 112,
        "clasificacion": "PG",
        "idioma_original": "Espanol",
        "director": "Lucia Ferreira",
        "reparto": "Beto Salgado, Cami Duran, Nico Peralta, Sole Aguirre",
        "calificacion": Decimal("7.9"),
        "fecha_estreno": date(2026, 6, 26),
        "generos": ["Comedia", "Aventura"],
    },
    {
        "titulo": "Papel y Ceniza",
        "titulo_original": "Paper and Ash",
        "sinopsis": "Una archivista descubre que los documentos que restaura estan "
        "siendo alterados despues de salir de sus manos. Seguir el rastro la lleva a un "
        "edificio que oficialmente nunca existio.",
        "duracion_min": 134,
        "clasificacion": "R",
        "idioma_original": "Frances",
        "director": "Camille Roux",
        "reparto": "Agnes Dubois, Marc Leclerc, Ines Ferrand",
        "calificacion": Decimal("8.1"),
        "fecha_estreno": date(2026, 4, 17),
        "generos": ["Suspenso", "Drama"],
    },
    {
        "titulo": "Los Guardianes del Faro",
        "titulo_original": "Lighthouse Keepers",
        "sinopsis": "Dos ninos y una gata encuentran un faro que dejo de funcionar hace "
        "cincuenta anos. Encenderlo otra vez despierta a los barcos que nunca llegaron a "
        "puerto.",
        "duracion_min": 97,
        "clasificacion": "G",
        "idioma_original": "Ingles",
        "director": "Hana Oyelaran",
        "reparto": "Voces de Mia Torres, Leo Fontana, Ruth Adeyemi",
        "calificacion": Decimal("8.6"),
        "fecha_estreno": date(2026, 7, 10),
        "generos": ["Animacion", "Aventura", "Fantasia"],
    },
    {
        "titulo": "Kilometro 44",
        "titulo_original": "Kilometer 44",
        "sinopsis": "Un camionero acepta una carga sin preguntar y descubre a mitad de "
        "ruta que lo persiguen dos autos que no aparecen en ningun radar.",
        "duracion_min": 118,
        "clasificacion": "R",
        "idioma_original": "Espanol",
        "director": "Rafael Quintana",
        "reparto": "Hector Amaya, Vera Solis, Tomas Ibarra",
        "calificacion": Decimal("7.4"),
        "fecha_estreno": date(2026, 6, 5),
        "generos": ["Accion", "Suspenso"],
    },
    {
        "titulo": "Todo lo que No Dijimos",
        "titulo_original": "Everything We Left Unsaid",
        "sinopsis": "Dos personas que se separaron hace doce anos quedan atrapadas por "
        "una tormenta en el mismo aeropuerto. Tienen una noche para decidir si vale la "
        "pena volver a empezar.",
        "duracion_min": 103,
        "clasificacion": "PG-13",
        "idioma_original": "Ingles",
        "director": "Priya Menon",
        "reparto": "Claire Nyong, Adam Ferraro",
        "calificacion": Decimal("7.8"),
        "fecha_estreno": date(2026, 5, 8),
        "generos": ["Drama", "Comedia"],
    },
    {
        "titulo": "Reino Sumergido",
        "titulo_original": "The Drowned Kingdom",
        "sinopsis": "Una arqueologa marina encuentra una ciudad bajo el hielo antartico "
        "y con ella un idioma que su cerebro entiende antes de haberlo aprendido.",
        "duracion_min": 149,
        "clasificacion": "PG-13",
        "idioma_original": "Ingles",
        "director": "Bjorn Ellefsen",
        "reparto": "Sigrid Holm, Amara Diallo, Peter Vance",
        "calificacion": Decimal("8.2"),
        "fecha_estreno": date(2026, 7, 17),
        "generos": ["Aventura", "Ciencia ficcion", "Fantasia"],
    },
    {
        "titulo": "Sala 7",
        "titulo_original": "Screen 7",
        "sinopsis": "Documental sobre las ultimas salas de cine independientes que siguen "
        "proyectando en 35mm, filmado durante tres anos en once ciudades.",
        "duracion_min": 88,
        "clasificacion": "PG",
        "idioma_original": "Multiple",
        "director": "Yusuf Karam",
        "reparto": "Proyeccionistas de once ciudades",
        "calificacion": Decimal("8.0"),
        "fecha_estreno": date(2026, 3, 20),
        "generos": ["Documental"],
    },
    {
        "titulo": "Velocidad de Escape",
        "titulo_original": "Escape Velocity",
        "sinopsis": "Un piloto de pruebas tiene noventa segundos para decidir si abandona "
        "el prototipo o lo lleva mas alla del limite que su empresa juro no cruzar.",
        "duracion_min": 124,
        "clasificacion": "PG-13",
        "idioma_original": "Ingles",
        "director": "Dana Whitfield",
        "reparto": "Ivan Petrov, Grace Abioye, Ken Matsuda",
        "calificacion": Decimal("7.7"),
        "fecha_estreno": date(2026, 6, 19),
        "generos": ["Accion", "Ciencia ficcion"],
    },
    {
        "titulo": "La Cocina de Medianoche",
        "titulo_original": "Midnight Kitchen",
        "sinopsis": "Un cocinero abre su local solo entre la una y las cinco de la "
        "manana. Cada plato que sirve resuelve algo que el comensal no sabia que "
        "necesitaba resolver.",
        "duracion_min": 109,
        "clasificacion": "PG",
        "idioma_original": "Japones",
        "director": "Aiko Murakami",
        "reparto": "Ryo Tanabe, Hikari Sato, Jun Morikawa",
        "calificacion": Decimal("8.5"),
        "fecha_estreno": date(2026, 5, 15),
        "generos": ["Drama", "Comedia", "Fantasia"],
    },
]

CINES = [
    {
        "nombre": "Cinema Aurora",
        "direccion": "Av. Larco 1301, Miraflores",
        "ciudad": "Lima",
        "telefono": "014101234",
        "salas": [
            {"nombre": "Sala 1", "tipo_sala": "2D", "filas": 8, "por_fila": 12},
            {"nombre": "Sala 2", "tipo_sala": "3D", "filas": 9, "por_fila": 14},
            {"nombre": "Sala 3", "tipo_sala": "IMAX", "filas": 10, "por_fila": 16},
            {"nombre": "Sala 4", "tipo_sala": "4DX", "filas": 7, "por_fila": 10},
        ],
    },
    {
        "nombre": "Cinema Aurora Norte",
        "direccion": "Av. Espana 1900, Trujillo",
        "ciudad": "Trujillo",
        "telefono": "044123456",
        "salas": [
            {"nombre": "Sala 1", "tipo_sala": "2D", "filas": 8, "por_fila": 12},
            {"nombre": "Sala 2", "tipo_sala": "3D", "filas": 9, "por_fila": 14},
        ],
    },
]

HORARIOS = [time(12, 30), time(15, 15), time(18, 0), time(20, 45), time(23, 15)]
IDIOMAS = ["Espanol", "Ingles"]
PRECIOS = {"2D": Decimal("85.00"), "3D": Decimal("110.00"), "IMAX": Decimal("145.00"), "4DX": Decimal("165.00")}


class Command(BaseCommand):
    help = "Carga catalogo, cines, salas, asientos y funciones de demostracion"

    def add_arguments(self, parser):
        parser.add_argument("--dias", type=int, default=8)
        parser.add_argument("--reset", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260721)
        if options["reset"]:
            self._reset()

        generos = self._generos()
        peliculas = self._peliculas(generos)
        salas = self._infraestructura()
        creadas = self._funciones(peliculas, salas, options["dias"])
        self._usuarios()

        self.stdout.write(self.style.SUCCESS(f"Generos: {len(generos)}"))
        self.stdout.write(self.style.SUCCESS(f"Peliculas: {len(peliculas)}"))
        self.stdout.write(self.style.SUCCESS(f"Salas: {len(salas)}"))
        self.stdout.write(self.style.SUCCESS(f"Funciones creadas: {creadas}"))
        self.stdout.write(self.style.SUCCESS("Listo. admin@cine.pe / demo@cine.pe con clave Cine2026!"))

    def _reset(self):
        from apps.payments.models import Pago, Ticket
        from apps.reservations.models import Reserva, ReservaAsiento
        from apps.showtimes.models import FuncionAsiento

        Ticket.objects.all().delete()
        Pago.objects.all().delete()
        ReservaAsiento.objects.all().delete()
        Reserva.objects.all().delete()
        FuncionAsiento.objects.all().delete()
        Funcion.objects.all().delete()
        Asiento.objects.all().delete()
        Sala.objects.all().delete()
        Cine.objects.all().delete()
        PeliculaGenero.objects.all().delete()
        Pelicula.objects.all().delete()
        Genero.objects.all().delete()

    def _generos(self):
        registros = {}
        for nombre in GENEROS:
            genero, _ = Genero.objects.get_or_create(nombre=nombre)
            registros[nombre] = genero
        return registros

    def _peliculas(self, generos):
        registros = []
        for datos in PELICULAS:
            nombres = datos.get("generos", [])
            defaults = {
                clave: valor
                for clave, valor in datos.items()
                if clave not in ("titulo", "generos")
            }
            pelicula, _ = Pelicula.objects.update_or_create(
                titulo=datos["titulo"], defaults=defaults
            )
            for nombre in nombres:
                PeliculaGenero.objects.get_or_create(
                    pelicula=pelicula, genero=generos[nombre]
                )
            registros.append(pelicula)
        return registros

    def _infraestructura(self):
        salas = []
        for datos_cine in CINES:
            cine, _ = Cine.objects.update_or_create(
                nombre=datos_cine["nombre"],
                defaults={
                    "direccion": datos_cine["direccion"],
                    "ciudad": datos_cine["ciudad"],
                    "telefono": datos_cine["telefono"],
                },
            )
            for datos_sala in datos_cine["salas"]:
                capacidad = datos_sala["filas"] * datos_sala["por_fila"]
                sala, _ = Sala.objects.update_or_create(
                    cine=cine,
                    nombre=datos_sala["nombre"],
                    defaults={
                        "tipo_sala": datos_sala["tipo_sala"],
                        "capacidad": capacidad,
                    },
                )
                self._asientos(sala, datos_sala["filas"], datos_sala["por_fila"])
                salas.append(sala)
        return salas

    def _asientos(self, sala, filas, por_fila):
        if sala.asientos.exists():
            return
        letras = [chr(ord("A") + indice) for indice in range(filas)]
        nuevos = []
        for indice, letra in enumerate(letras):
            for numero in range(1, por_fila + 1):
                if indice >= filas - 2:
                    tipo = TipoAsiento.VIP
                elif indice == 0 and numero in (1, 2, por_fila - 1, por_fila):
                    tipo = TipoAsiento.DISCAPACITADO
                else:
                    tipo = TipoAsiento.ESTANDAR
                nuevos.append(
                    Asiento(sala=sala, fila=letra, numero=numero, tipo=tipo)
                )
        Asiento.objects.bulk_create(nuevos, batch_size=500)

    def _funciones(self, peliculas, salas, dias):
        zona = timezone.get_current_timezone()
        hoy = timezone.localdate()
        creadas = 0
        for desplazamiento in range(dias):
            dia = hoy + timedelta(days=desplazamiento)
            for sala in salas:
                seleccion = random.sample(peliculas, min(3, len(peliculas)))
                for indice, hora in enumerate(HORARIOS):
                    pelicula = seleccion[indice % len(seleccion)]
                    inicio = timezone.make_aware(datetime.combine(dia, hora), zona)
                    if inicio <= timezone.now() + timedelta(minutes=30):
                        continue
                    fin = inicio + timedelta(minutes=pelicula.duracion_min + 20)
                    precio = PRECIOS.get(sala.tipo_sala, Decimal("85.00"))
                    if desplazamiento == 0:
                        precio = precio - Decimal("15.00")
                    funcion, nueva = Funcion.objects.get_or_create(
                        sala=sala,
                        fecha_hora_inicio=inicio,
                        defaults={
                            "pelicula": pelicula,
                            "fecha_hora_fin": fin,
                            "idioma": random.choice(IDIOMAS),
                            "subtitulos": random.random() > 0.5,
                            "precio_base": precio,
                        },
                    )
                    if nueva:
                        generar_asientos_de_funcion(funcion)
                        self._ocupacion_inicial(funcion)
                        creadas += 1
        return creadas

    def _ocupacion_inicial(self, funcion):
        from apps.showtimes.models import EstadoFuncionAsiento, FuncionAsiento

        ids = list(
            FuncionAsiento.objects.filter(funcion=funcion).values_list("id", flat=True)
        )
        if not ids:
            return
        cuantos = int(len(ids) * random.uniform(0.05, 0.35))
        ocupados = random.sample(ids, cuantos)
        FuncionAsiento.objects.filter(id__in=ocupados).update(
            estado=EstadoFuncionAsiento.OCUPADO
        )

    def _usuarios(self):
        if not Usuario.objects.filter(email="admin@cine.pe").exists():
            Usuario.objects.create_superuser(
                email="admin@cine.pe",
                password="Cine2026!",
                nombre="Alexis",
                apellido="Admin",
            )
        if not Usuario.objects.filter(email="demo@cine.pe").exists():
            Usuario.objects.create_user(
                email="demo@cine.pe",
                password="Cine2026!",
                nombre="Cliente",
                apellido="Demo",
                telefono="987654321",
                email_verificado=True,
            )
