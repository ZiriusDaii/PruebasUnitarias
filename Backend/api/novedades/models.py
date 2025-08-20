from django.db import models
from api.base.base import BaseModel
from django.utils import timezone
from django.core.exceptions import ValidationError
from api.manicuristas.models import Manicurista
from datetime import time, timedelta


class Novedad(BaseModel):
    ESTADO_CHOICES = (
        ('ausente', 'Ausente'),
        ('tardanza', 'Tardanza'),
        ('anulada', 'Anulada'),
    )

    TIPO_AUSENCIA_CHOICES = (
        ('completa', 'Día Completo'),
        ('por_horas', 'Por Horas'),
    )

    # Horarios base del negocio (10am - 8pm)
    HORA_ENTRADA_BASE = time(10, 0)  # 10:00 AM
    HORA_SALIDA_BASE = time(20, 0)   # 8:00 PM
    HORA_MIN_PERMITIDA = time(7, 0)  # 7:00 AM
    HORA_MAX_PERMITIDA = time(22, 0) # 10:00 PM

    fecha = models.DateField()
    hora_entrada = models.TimeField(null=True, blank=True)
    hora_salida = models.TimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES)
    tipo_ausencia = models.CharField(max_length=10, choices=TIPO_AUSENCIA_CHOICES, null=True, blank=True)
    hora_inicio_ausencia = models.TimeField(null=True, blank=True)
    hora_fin_ausencia = models.TimeField(null=True, blank=True)
    motivo = models.TextField(blank=True, null=True)
    manicurista = models.ForeignKey(Manicurista, on_delete=models.CASCADE)
    
    # Campos para anulación
    motivo_anulacion = models.TextField(blank=True, null=True)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)

    def clean(self):
        super().clean()
        
        # No validar duplicados para novedades anuladas
        if self.estado != 'anulada':
            # Validar que no haya duplicados activos para la misma manicurista y fecha
            existing_query = Novedad.objects.filter(
                manicurista=self.manicurista, 
                fecha=self.fecha
            ).exclude(estado='anulada')
            
            if self.pk:
                existing_query = existing_query.exclude(pk=self.pk)
                
            if existing_query.exists():
                raise ValidationError("Ya existe una novedad activa para esta manicurista en la fecha indicada.")
        
        # Validar fecha según el estado
        if self.estado != 'anulada':
            today = timezone.now().date()
            tomorrow = today + timedelta(days=1)
            
            if self.estado == 'ausente':
                if self.fecha < tomorrow:
                    raise ValidationError({
                        'fecha': 'Para ausencias, debe seleccionar una fecha a partir de mañana. '
                                'Las ausencias deben programarse con al menos un día de anticipación.'
                    })
            elif self.estado == 'tardanza':
                if self.fecha < today:
                    raise ValidationError({
                        'fecha': 'Para tardanzas, debe seleccionar una fecha a partir de hoy.'
                    })
            else:
                # Validación general
                if self.fecha < today:
                    raise ValidationError({
                        'fecha': 'No se puede registrar una novedad en fecha anterior a hoy.'
                    })

    def save(self, *args, **kwargs):
        # Solo validar si no es anulada
        if self.estado != 'anulada':
            self.full_clean()
        super().save(*args, **kwargs)

    def anular(self, motivo):
        """Método para anular una novedad"""
        self.estado = 'anulada'
        self.motivo_anulacion = motivo
        self.fecha_anulacion = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.manicurista} - {self.estado} ({self.fecha})"

    class Meta:
        verbose_name_plural = "Novedades"
        ordering = ['-fecha', '-created_at']
        # Remover unique_together para permitir múltiples registros (incluyendo anuladas)
