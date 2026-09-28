from django.contrib import admin

from .models import Reserva, ReservaAsiento


class ReservaAsientoInline(admin.TabularInline):
    model = ReservaAsiento
    extra = 0
    readonly_fields = ("funcion_asiento", "precio_pagado")


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("codigo_reserva", "usuario", "funcion", "estado", "total", "expira_en")
    list_filter = ("estado",)
    search_fields = ("codigo_reserva", "usuario__email")
    date_hierarchy = "created_at"
    inlines = [ReservaAsientoInline]
