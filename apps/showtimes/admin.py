from django.contrib import admin

from .models import Asiento, Cine, Funcion, FuncionAsiento, Sala


@admin.register(Cine)
class CineAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ciudad", "telefono")
    search_fields = ("nombre", "ciudad")


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "cine", "tipo_sala", "capacidad", "activa")
    list_filter = ("cine", "tipo_sala", "activa")


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    list_display = ("sala", "fila", "numero", "tipo", "activo")
    list_filter = ("sala", "tipo", "activo")


@admin.register(Funcion)
class FuncionAdmin(admin.ModelAdmin):
    list_display = ("pelicula", "sala", "fecha_hora_inicio", "precio_base", "activa")
    list_filter = ("activa", "sala__cine", "sala__tipo_sala")
    date_hierarchy = "fecha_hora_inicio"
    autocomplete_fields = ("pelicula",)


@admin.register(FuncionAsiento)
class FuncionAsientoAdmin(admin.ModelAdmin):
    list_display = ("funcion", "asiento", "estado", "precio", "reservado_hasta")
    list_filter = ("estado",)
