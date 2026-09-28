from datetime import datetime
from decimal import Decimal

import requests
from decouple import config
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.movies.models import Genero, Pelicula

TMDB_BASE_URL = "https://api.themoviedb.org/3"

TITULOS_A_IMPORTAR = [
    "Dune: Part Two",
    "Oppenheimer",
    "Barbie",
    "Spider-Man: Across the Spider-Verse",
    "The Batman",
    "Everything Everywhere All at Once",
    "Interstellar",
    "Get Out",
    "Free Solo",
    "Coco",
    "Deadpool & Wolverine",
    "La La Land",
]

GENEROS_TMDB_A_LOCAL = {
    28: "Accion",
    12: "Aventura",
    16: "Animacion",
    878: "Ciencia ficcion",
    35: "Comedia",
    99: "Documental",
    18: "Drama",
    14: "Fantasia",
    53: "Suspenso",
    27: "Terror",
}

IDIOMAS_ISO_A_ESPANOL = {
    "en": "Ingles",
    "es": "Espanol",
    "ja": "Japones",
    "fr": "Frances",
    "ko": "Coreano",
    "de": "Aleman",
    "it": "Italiano",
    "pt": "Portugues",
    "zh": "Chino",
    "hi": "Hindi",
}


class Command(BaseCommand):
    help = "Reemplaza el catalogo actual de peliculas con datos reales de TMDB, en el lugar (mismo id)"

    def handle(self, *args, **options):
        api_key = config("TMDB_API_KEY", default="")
        if not api_key:
            raise CommandError(
                "Falta TMDB_API_KEY en el .env. Agrega tu API key de themoviedb.org."
            )

        peliculas = list(Pelicula.objects.order_by("id"))
        if len(peliculas) != len(TITULOS_A_IMPORTAR):
            raise CommandError(
                f"Se esperaban {len(TITULOS_A_IMPORTAR)} peliculas existentes, "
                f"hay {len(peliculas)}. Revisa la base antes de continuar."
            )

        generos_locales = {genero.nombre: genero for genero in Genero.objects.all()}

        with transaction.atomic():
            for pelicula, titulo_buscado in zip(peliculas, TITULOS_A_IMPORTAR):
                self._importar_una(api_key, pelicula, titulo_buscado, generos_locales)

    def _get(self, ruta, api_key, **params):
        params["api_key"] = api_key
        respuesta = requests.get(f"{TMDB_BASE_URL}{ruta}", params=params, timeout=15)
        respuesta.raise_for_status()
        return respuesta.json()

    def _importar_una(self, api_key, pelicula, titulo_buscado, generos_locales):
        titulo_viejo = pelicula.titulo

        busqueda = self._get(
            "/search/movie", api_key, query=titulo_buscado, language="es-MX"
        )
        resultados = busqueda.get("results") or []
        if not resultados:
            raise CommandError(f"TMDB no devolvio resultados para '{titulo_buscado}'")
        tmdb_id = resultados[0]["id"]

        detalle = self._get(
            f"/movie/{tmdb_id}",
            api_key,
            language="es-MX",
            append_to_response="credits,videos,release_dates",
        )

        sinopsis = detalle.get("overview") or ""
        if not sinopsis:
            detalle_en = self._get(f"/movie/{tmdb_id}", api_key, language="en-US")
            sinopsis = detalle_en.get("overview") or ""

        pelicula.titulo = detalle.get("title") or titulo_buscado
        pelicula.titulo_original = detalle.get("original_title") or None
        pelicula.sinopsis = sinopsis or None
        pelicula.duracion_min = detalle.get("runtime") or pelicula.duracion_min
        pelicula.clasificacion = self._certificacion_us(detalle)
        pelicula.poster_url = self._url_imagen(detalle.get("poster_path"), "w500")
        pelicula.backdrop_url = self._url_imagen(detalle.get("backdrop_path"), "w1280")
        pelicula.trailer_url = self._trailer(detalle)
        pelicula.idioma_original = IDIOMAS_ISO_A_ESPANOL.get(
            detalle.get("original_language", ""), (detalle.get("original_language") or "").upper()
        )
        pelicula.director = self._director(detalle)
        pelicula.reparto = self._reparto(detalle)
        pelicula.reparto_detalle = self._reparto_detalle(detalle)
        pelicula.calificacion = Decimal(str(round(detalle.get("vote_average") or 0, 1)))
        pelicula.fecha_estreno = self._fecha_estreno(detalle)
        pelicula.activa = True
        pelicula.save()

        nombres_genero = [
            GENEROS_TMDB_A_LOCAL[g["id"]]
            for g in detalle.get("genres", [])
            if g["id"] in GENEROS_TMDB_A_LOCAL
        ]
        pelicula.generos.set(
            [generos_locales[nombre] for nombre in nombres_genero if nombre in generos_locales]
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"[{pelicula.id}] {titulo_viejo!r} -> {pelicula.titulo!r} "
                f"({'con poster' if pelicula.poster_url else 'sin poster'})"
            )
        )

    @staticmethod
    def _url_imagen(path, tamano):
        if not path:
            return None
        return f"https://image.tmdb.org/t/p/{tamano}{path}"

    @staticmethod
    def _certificacion_us(detalle):
        for pais in detalle.get("release_dates", {}).get("results", []):
            if pais.get("iso_3166_1") != "US":
                continue
            for entrada in pais.get("release_dates", []):
                if entrada.get("certification"):
                    return entrada["certification"]
        return ""

    @staticmethod
    def _trailer(detalle):
        videos = detalle.get("videos", {}).get("results", [])
        candidatos = [
            v for v in videos if v.get("site") == "YouTube" and v.get("type") == "Trailer"
        ]
        if not candidatos:
            return None
        oficiales = [v for v in candidatos if v.get("official")]
        elegido = oficiales[0] if oficiales else candidatos[0]
        return f"https://www.youtube.com/watch?v={elegido['key']}"

    @staticmethod
    def _director(detalle):
        crew = detalle.get("credits", {}).get("crew", [])
        directores = [p["name"] for p in crew if p.get("job") == "Director"]
        return ", ".join(directores) or None

    @staticmethod
    def _reparto(detalle):
        cast = detalle.get("credits", {}).get("cast", [])
        nombres = [p["name"] for p in cast[:5]]
        return ", ".join(nombres) or None

    @staticmethod
    def _reparto_detalle(detalle):
        cast = detalle.get("credits", {}).get("cast", [])
        return [
            {
                "nombre": p["name"],
                "personaje": p.get("character") or None,
                "foto_url": (
                    f"https://image.tmdb.org/t/p/w300{p['profile_path']}"
                    if p.get("profile_path")
                    else None
                ),
            }
            for p in cast[:8]
        ]

    @staticmethod
    def _fecha_estreno(detalle):
        release_date = detalle.get("release_date")
        if not release_date:
            return None
        return datetime.strptime(release_date, "%Y-%m-%d").date()
