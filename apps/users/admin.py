from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ("-created_at",)
    list_display = ("email", "nombre", "apellido", "rol", "is_active", "created_at")
    list_filter = ("rol", "is_active", "email_verificado")
    search_fields = ("email", "nombre", "apellido")
    readonly_fields = ("created_at", "updated_at", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Perfil", {"fields": ("nombre", "apellido", "telefono")}),
        ("Permisos", {"fields": ("rol", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nombre", "apellido", "password1", "password2", "rol"),
            },
        ),
    )
