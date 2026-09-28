from django.core.validators import MinValueValidator
from django.db import models


class Genero(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "generos"
        ordering = ["nombre"]
        verbose_name = "genero"
        verbose_name_plural = "generos"

    def __str__(self):
        return self.nombre


class PeliculaQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(activa=True)

    def con_generos(self):
        return self.prefetch_related("generos")


class Pelicula(models.Model):
    titulo = models.CharField(max_length=200)
    titulo_original = models.CharField(max_length=200, blank=True, null=True)
    sinopsis = models.TextField(blank=True, null=True)
    duracion_min = models.IntegerField(validators=[MinValueValidator(1)])
    clasificacion = models.CharField(max_length=10, blank=True, null=True)
    poster_url = models.CharField(max_length=500, blank=True, null=True)
    backdrop_url = models.CharField(max_length=500, blank=True, null=True)
    trailer_url = models.CharField(max_length=500, blank=True, null=True)
    idioma_original = models.CharField(max_length=50, blank=True, null=True)
    director = models.CharField(max_length=150, blank=True, null=True)
    reparto = models.CharField(max_length=400, blank=True, null=True)
    reparto_detalle = models.JSONField(default=list, blank=True)
    calificacion = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    fecha_estreno = models.DateField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    generos = models.ManyToManyField(
        Genero, through="PeliculaGenero", related_name="peliculas"
    )

    objects = PeliculaQuerySet.as_manager()

    class Meta:
        db_table = "peliculas"
        ordering = ["-fecha_estreno", "titulo"]
        verbose_name = "pelicula"
        verbose_name_plural = "peliculas"
        indexes = [models.Index(fields=["activa"], name="idx_peliculas_activa")]

    def __str__(self):
        return self.titulo

    @property
    def duracion_legible(self):
        horas, minutos = divmod(self.duracion_min, 60)
        return f"{horas}h {minutos:02d}m" if horas else f"{minutos}m"


class PeliculaGenero(models.Model):
    pelicula = models.ForeignKey(
        Pelicula, on_delete=models.CASCADE, db_column="pelicula_id"
    )
    genero = models.ForeignKey(Genero, on_delete=models.CASCADE, db_column="genero_id")

    class Meta:
        db_table = "pelicula_generos"
        constraints = [
            models.UniqueConstraint(
                fields=["pelicula", "genero"], name="uq_pelicula_genero"
            )
        ]
