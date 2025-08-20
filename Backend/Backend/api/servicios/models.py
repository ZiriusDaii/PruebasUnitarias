from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, URLValidator
from django.core.exceptions import ValidationError
from api.base.base import BaseModel


class Servicio(BaseModel):
    ESTADO_ACTIVO = 'activo'
    ESTADO_INACTIVO = 'inactivo'
    ESTADO_CHOICES = [
        (ESTADO_ACTIVO, 'Activo'),
        (ESTADO_INACTIVO, 'Inactivo'),
    ]

    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre del servicio"
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio"
    )

    descripcion = models.TextField(
        verbose_name="Descripción"
    )

    duracion = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(600)],
        verbose_name="Duración en minutos",
        help_text="Duración del servicio en minutos (1-600)"
    )

    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default=ESTADO_ACTIVO,
        verbose_name="Estado"
    )

    imagen = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL de la imagen",
        validators=[URLValidator()]
    )

    class Meta:
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nombre} ({self.duracion} min)"

    def clean(self):
        """
        Validaciones adicionales (se aplican solo si llamas full_clean()).
        """
        # Asegurarse que el nombre no sea solo espacios
        if self.nombre and not self.nombre.strip():
            raise ValidationError({'nombre': "El nombre no puede estar vacío."})

        # Validar precio manualmente si necesitas más control
        if self.precio is not None and self.precio < 0:
            raise ValidationError({'precio': "El precio no puede ser negativo."})
        
        # Validar duración
        if self.duracion is not None:
            if self.duracion < 1:
                raise ValidationError({'duracion': "La duración debe ser al menos 1 minuto."})
            elif self.duracion > 600:
                raise ValidationError({'duracion': "La duración no puede exceder 600 minutos."})

    @property
    def duracion_formateada(self):
        """Retorna la duración en formato legible"""
        if self.duracion < 60:
            return f"{self.duracion} min"
        else:
            horas = self.duracion // 60
            minutos = self.duracion % 60
            if minutos == 0:
                return f"{horas}h"
            else:
                return f"{horas}h {minutos}min"
