from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.db.models import Sum


class Liquidacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('cancelado', 'Cancelado'),
    ]

    manicurista = models.ForeignKey(
        'manicuristas.Manicurista',
        on_delete=models.CASCADE,
        related_name='liquidaciones'
    )
    fecha_inicio = models.DateField()
    fecha_final = models.DateField()
    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Valor base de la liquidación"
    )
    bonificacion = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Bonificación adicional"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'liquidaciones'
        verbose_name = 'Liquidación'
        verbose_name_plural = 'Liquidaciones'
        ordering = ['-fecha_inicio']
        unique_together = ['manicurista', 'fecha_inicio', 'fecha_final']

    def __str__(self):
        return f"Liquidación {self.manicurista.nombres} {self.manicurista.apellidos} - {self.fecha_inicio} a {self.fecha_final}"

    @property
    def total_a_pagar(self):
        """Calcula el total a pagar (valor + bonificación)"""
        return self.valor + self.bonificacion

    @property
    def total_servicios_completados(self):
        """Calcula el total de servicios completados en el período"""
        from api.citas.models import Cita
        
        total = Cita.objects.filter(
            manicurista=self.manicurista,
            fecha_cita__range=(self.fecha_inicio, self.fecha_final),
            estado='finalizada'
        ).aggregate(total=Sum('precio_servicio'))['total']
        
        return total or Decimal('0.00')

    @property
    def citascompletadas(self):
        """Calcula la comisión del 50% de las citas completadas"""
        return self.total_servicios_completados * Decimal('0.5')

    @property
    def cantidad_servicios_completados(self):
        """Cuenta la cantidad de servicios completados"""
        from api.citas.models import Cita
        
        return Cita.objects.filter(
            manicurista=self.manicurista,
            fecha_cita__range=(self.fecha_inicio, self.fecha_final),
            estado='finalizada'
        ).count()

    def calcular_citas_completadas(self):
        """Método para recalcular las citas completadas"""
        return self.citascompletadas

    def recalcular_citas_completadas(self):
        """Método para recalcular y actualizar las citas completadas"""
        nuevo_valor = self.calcular_citas_completadas()
        # Aquí podrías actualizar algún campo si fuera necesario
        return nuevo_valor

    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.fecha_final < self.fecha_inicio:
            raise ValidationError('La fecha final debe ser posterior a la fecha de inicio')
        
        if self.valor < 0:
            raise ValidationError('El valor no puede ser negativo')
        
        if self.bonificacion < 0:
            raise ValidationError('La bonificación no puede ser negativa')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
