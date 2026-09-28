from django.contrib import admin

from .models import Genero, Pelicula, PeliculaGenero


class PeliculaGeneroInline(admin.TabularInline):
    model = PeliculaGenero
    extra = 1


@admin.register(Genero)
class GeneroAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Pelicula)
class PeliculaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "duracion_min", "clasificacion", "fecha_estreno", "activa")
    list_filter = ("activa", "clasificacion", "generos")
    search_fields = ("titulo", "titulo_original", "director")
    inlines = [PeliculaGeneroInline]
