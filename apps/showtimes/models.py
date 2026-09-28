from django.db import models
from django.db.models import Q
from django.utils import timezone


class TipoAsiento(models.TextChoices):
    ESTANDAR = "estandar", "Estandar"
    VIP = "vip", "VIP"
    DISCAPACITADO = "discapacitado", "Accesible"


class EstadoFuncionAsiento(models.TextChoices):
    DISPONIBLE = "disponible", "Disponible"
    RESERVADO = "reservado", "Reservado"
    OCUPADO = "ocupado", "Ocupado"
    BLOQUEADO = "bloqueado", "Bloqueado"


class Cine(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField(max_length=300, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = "cines"
        ordering = ["nombre"]
        verbose_name = "cine"
        verbose_name_plural = "cines"

    def __str__(self):
        return self.nombre


class Sala(models.Model):
    id = models.AutoField(primary_key=True)
    cine = models.ForeignKey(
        Cine, on_delete=models.CASCADE, related_name="salas", db_column="cine_id"
    )
    nombre = models.CharField(max_length=50)
    tipo_sala = models.CharField(max_length=20, default="2D")
    capacidad = models.IntegerField()
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "salas"
        ordering = ["cine_id", "nombre"]
        verbose_name = "sala"
        verbose_name_plural = "salas"
        constraints = [
            models.UniqueConstraint(fields=["cine", "nombre"], name="uq_sala_cine_nombre")
        ]

    def __str__(self):
        return f"{self.cine.nombre} - {self.nombre}"


class Asiento(models.Model):
    sala = models.ForeignKey(
        Sala, on_delete=models.CASCADE, related_name="asientos", db_column="sala_id"
    )
    fila = models.CharField(max_length=2)
    numero = models.IntegerField()
    tipo = models.CharField(
        max_length=20, choices=TipoAsiento.choices, default=TipoAsiento.ESTANDAR
    )
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "asientos"
        ordering = ["fila", "numero"]
        verbose_name = "asiento"
        verbose_name_plural = "asientos"
        constraints = [
            models.UniqueConstraint(
                fields=["sala", "fila", "numero"], name="uq_asiento_sala_fila_numero"
            )
        ]

    def __str__(self):
        return f"{self.fila}{self.numero}"

    @property
    def etiqueta(self):
        return f"{self.fila}{self.numero}"


class FuncionQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(activa=True)

    def futuras(self):
        return self.filter(fecha_hora_inicio__gt=timezone.now())

    def completas(self):
        return self.select_related("pelicula", "sala", "sala__cine")


class Funcion(models.Model):
    pelicula = models.ForeignKey(
        "movies.Pelicula",
        on_delete=models.PROTECT,
        related_name="funciones",
        db_column="pelicula_id",
    )
    sala = models.ForeignKey(
        Sala, on_delete=models.PROTECT, related_name="funciones", db_column="sala_id"
    )
    fecha_hora_inicio = models.DateTimeField()
    fecha_hora_fin = models.DateTimeField()
    idioma = models.CharField(max_length=50, blank=True, null=True)
    subtitulos = models.BooleanField(default=False)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FuncionQuerySet.as_manager()

    class Meta:
        db_table = "funciones"
        ordering = ["fecha_hora_inicio"]
        verbose_name = "funcion"
        verbose_name_plural = "funciones"
        indexes = [
            models.Index(fields=["sala", "fecha_hora_inicio"], name="idx_func_sala_horario"),
            models.Index(fields=["pelicula"], name="idx_func_pelicula"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_hora_fin__gt=models.F("fecha_hora_inicio")),
                name="ck_funcion_rango_horario",
            ),
            models.CheckConstraint(
                condition=Q(precio_base__gte=0), name="ck_funcion_precio_positivo"
            ),
        ]

    def __str__(self):
        return f"{self.pelicula.titulo} - {self.fecha_hora_inicio:%d/%m %H:%M}"

    @property
    def ya_empezo(self):
        return self.fecha_hora_inicio <= timezone.now()


class FuncionAsiento(models.Model):
    funcion = models.ForeignKey(
        Funcion,
        on_delete=models.CASCADE,
        related_name="funcion_asientos",
        db_column="funcion_id",
    )
    asiento = models.ForeignKey(
        Asiento,
        on_delete=models.PROTECT,
        related_name="funcion_asientos",
        db_column="asiento_id",
    )
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoFuncionAsiento.choices,
        default=EstadoFuncionAsiento.DISPONIBLE,
    )
    reservado_hasta = models.DateTimeField(blank=True, null=True)
    version = models.IntegerField(default=0)

    class Meta:
        db_table = "funcion_asientos"
        ordering = ["asiento__fila", "asiento__numero"]
        verbose_name = "asiento de funcion"
        verbose_name_plural = "asientos de funcion"
        indexes = [
            models.Index(fields=["funcion"], name="idx_fa_funcion"),
            models.Index(fields=["funcion", "estado"], name="idx_fa_funcion_estado"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["funcion", "asiento"], name="uq_funcion_asiento"
            )
        ]

    def __str__(self):
        return f"{self.funcion_id}:{self.asiento} [{self.estado}]"

    @property
    def hold_vencido(self):
        return (
            self.estado == EstadoFuncionAsiento.RESERVADO
            and self.reservado_hasta is not None
            and self.reservado_hasta < timezone.now()
        )

    @property
    def esta_libre(self):
        return self.estado == EstadoFuncionAsiento.DISPONIBLE or self.hold_vencido
