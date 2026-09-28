from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class RolUsuario(models.TextChoices):
    CLIENTE = "cliente", "Cliente"
    ADMIN = "admin", "Administrador"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("rol", RolUsuario.CLIENTE)
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("rol", RolUsuario.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verificado", True)
        extra.setdefault("nombre", "Admin")
        extra.setdefault("apellido", "Cine")
        if extra.get("is_staff") is not True:
            raise ValueError("El superusuario requiere is_staff=True")
        if extra.get("is_superuser") is not True:
            raise ValueError("El superusuario requiere is_superuser=True")
        return self._crear(email, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rol = models.CharField(
        max_length=20, choices=RolUsuario.choices, default=RolUsuario.CLIENTE
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    email_verificado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "apellido"]

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def es_admin(self):
        return self.rol == RolUsuario.ADMIN or self.is_superuser
