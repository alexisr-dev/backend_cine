from django.contrib import admin

from .models import Pago, Ticket


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("reserva", "monto", "metodo_pago", "estado", "procesado_en")
    list_filter = ("estado", "metodo_pago")
    search_fields = ("idempotency_key", "transaccion_externa_id", "reserva__codigo_reserva")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("codigo_qr", "reserva", "emitido_en")
    search_fields = ("codigo_qr", "reserva__codigo_reserva")
