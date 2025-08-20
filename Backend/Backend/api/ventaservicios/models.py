from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from api.base.base import BaseModel
from api.clientes.models import Cliente
from api.servicios.models import Servicio
from api.manicuristas.models import Manicurista
from decimal import Decimal


class VentaServicio(BaseModel):
    # MÉTODOS DE PAGO LIMITADOS COMO SOLICITASTE
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
    ]

    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        verbose_name="Cliente"
    )
    
    manicurista = models.ForeignKey(
        Manicurista,
        on_delete=models.CASCADE,
        verbose_name="Manicurista"
    )
    
    # Este campo 'servicio' se mantiene por compatibilidad o si una venta es de un solo servicio directo.
    # La lógica principal de servicios múltiples se maneja en DetalleVentaServicio.
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.SET_NULL, # Cambiado a SET_NULL
        null=True, # Permitir nulo
        blank=True, # Permitir en blanco
        verbose_name="Servicio principal (compatibilidad)"
    )
    
    # NUEVO: Soporte para múltiples citas
    citas = models.ManyToManyField(
        'citas.Cita',
        blank=True,
        verbose_name="Citas relacionadas",
        help_text="Citas asociadas a esta venta"
    )
    
    # MANTENER para compatibilidad
    cita = models.ForeignKey(
        'citas.Cita',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Cita principal",
        help_text="Cita principal (para compatibilidad)",
        related_name="ventas_principal"
    )
    
    # Estos campos (cantidad, precio_unitario, descuento) son para la venta principal si no hay detalles
    # O para compatibilidad. La lógica principal de precios/cantidades está en DetalleVentaServicio
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.0,
        verbose_name="Precio unitario"
    )
    
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Descuento aplicado"
    )
    
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Total"
    )
    
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo',
        verbose_name="Método de pago"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name="Estado"
    )
    
    # CORREGIDO: Usar DateTimeField para sincronizar con citas
    fecha_venta = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha y hora de venta"
    )
    
    fecha_pago = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de pago"
    )
    
    observaciones = models.TextField(
        blank=True,
        null=True,
        verbose_name="Observaciones"
    )
    
    # Campos para comisiones
    comision_manicurista = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Comisión manicurista"
    )
    
    porcentaje_comision = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Porcentaje de comisión"
    )

    class Meta:
        verbose_name = "Venta de Servicio"
        verbose_name_plural = "Ventas de Servicios"
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"Venta {self.id} - {self.cliente.nombre}" # Modificado para no depender de self.servicio

    def clean(self):
        """Validaciones personalizadas"""
        # Si hay detalles, el total se calcula a partir de ellos.
        # Si no hay detalles, se usa el servicio principal (para compatibilidad).
        if self.pk and self.detalles.exists():
            total_calculado = sum(detalle.subtotal for detalle in self.detalles.all())
            if abs(self.total - total_calculado) > Decimal('0.01'):
                raise ValidationError({
                    'total': f'El total debe ser {total_calculado}'
                })
        elif self.servicio and self.precio_unitario and self.cantidad:
            total_calculado = (self.precio_unitario * self.cantidad) - self.descuento
            if abs(self.total - total_calculado) > Decimal('0.01'):
                raise ValidationError({
                    'total': f'El total debe ser {total_calculado}'
                })
        
        # Validar que el descuento no sea mayor al subtotal (si aplica al servicio principal)
        if self.servicio and self.precio_unitario and self.cantidad and self.descuento:
            subtotal = self.precio_unitario * self.cantidad
            if self.descuento > subtotal:
                raise ValidationError({
                    'descuento': 'El descuento no puede ser mayor al subtotal del servicio principal'
                })

    def save(self, *args, **kwargs):
        # Si no hay detalles, usar el servicio principal para calcular total y precio_unitario
        if not self.detalles.exists():
            if self.servicio:
                if not self.precio_unitario:
                    self.precio_unitario = self.servicio.precio
                if not self.total:
                    self.total = (self.precio_unitario * self.cantidad) - self.descuento
            else:
                # Si no hay servicio principal ni detalles, asegurar que total sea 0
                self.total = Decimal('0.00')
        else:
            # Si hay detalles, el total se recalcula en la señal post_save de DetalleVentaServicio
            # Aquí solo aseguramos que el total inicial sea la suma de los detalles si ya existen
            if self.pk: # Solo si la instancia ya existe y tiene detalles
                self.total = sum(detalle.subtotal for detalle in self.detalles.all()) - self.descuento
            else: # Para nuevas ventas, el total se calculará después de guardar los detalles
                self.total = Decimal('0.00') # Valor temporal

        # Calcular comisión si hay porcentaje definido
        if self.porcentaje_comision and self.total is not None:
            self.comision_manicurista = (self.total * self.porcentaje_comision) / 100
        
        # Establecer fecha de pago cuando se marca como pagada
        if self.estado == 'pagada' and not self.fecha_pago:
            self.fecha_pago = timezone.now()
        
        super().save(*args, **kwargs)

    def sincronizar_con_citas(self):
        """Sincronizar información con las citas asociadas"""
        citas_asociadas = self.citas.all()
        if citas_asociadas.exists():
            # Usar la fecha de la primera cita como referencia
            primera_cita = citas_asociadas.first()
            if primera_cita:
                # Combinar fecha de cita con hora actual para mantener timestamp
                fecha_cita = primera_cita.fecha_cita
                hora_cita = primera_cita.hora_cita
                
                # Crear datetime combinando fecha y hora de la cita
                from datetime import datetime, time
                if isinstance(fecha_cita, str):
                    fecha_cita = datetime.strptime(fecha_cita, '%Y-%m-%d').date()
                if isinstance(hora_cita, str):
                    hora_cita = datetime.strptime(hora_cita, '%H:%M').time()
                
                fecha_venta_sincronizada = datetime.combine(fecha_cita, hora_cita)
                
                # Hacer timezone-aware
                if timezone.is_naive(fecha_venta_sincronizada):
                    fecha_venta_sincronizada = timezone.make_aware(fecha_venta_sincronizada)
                
                self.fecha_venta = fecha_venta_sincronizada
                
                # Mantener compatibilidad con cita principal
                if not self.cita:
                    self.cita = primera_cita
                
                self.save(update_fields=['fecha_venta', 'cita'])

    @property
    def subtotal(self):
        """Calcula el subtotal sin descuento (para el servicio principal si no hay detalles)"""
        if self.detalles.exists():
            return sum(detalle.subtotal for detalle in self.detalles.all())
        return self.precio_unitario * self.cantidad if self.precio_unitario and self.cantidad else Decimal('0.00')

    @property
    def total_con_descuento(self):
        """Calcula el total aplicando descuento (para el servicio principal si no hay detalles)"""
        return self.subtotal - self.descuento

    @property
    def puede_cancelar(self):
        """Verifica si la venta puede ser cancelada"""
        return self.estado in ['pendiente']

    @property
    def puede_marcar_pagada(self):
        """Verifica si la venta puede marcarse como pagada"""
        return self.estado == 'pendiente'

    @property
    def es_desde_cita(self):
        """Verifica si la venta fue creada desde una cita"""
        return self.cita is not None or self.citas.exists()

    @property
    def citas_info(self):
        """Obtener información de todas las citas asociadas"""
        return self.citas.all()

    def get_fecha_para_mostrar(self):
        """Obtener fecha formateada para mostrar en frontend"""
        if self.fecha_venta:
            return self.fecha_venta.strftime('%Y-%m-%d')
        return None

    def get_hora_para_mostrar(self):
        """Obtener hora formateada para mostrar en frontend"""
        if self.fecha_venta:
            return self.fecha_venta.strftime('%H:%M')
        return None


class DetalleVentaServicio(BaseModel):
    """Modelo para manejar ventas con múltiples servicios"""
    
    venta = models.ForeignKey(
        VentaServicio,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name="Venta"
    )
    
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        verbose_name="Servicio"
    )
    
    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Precio unitario"
    )
    
    descuento_linea = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Descuento línea"
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Subtotal"
    )

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    def __str__(self):
        return f"Detalle {self.venta.id} - {self.servicio.nombre}"

    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        if self.precio_unitario is None and self.servicio:
            self.precio_unitario = self.servicio.precio
        
        if self.precio_unitario is not None and self.cantidad is not None:
            self.subtotal = (self.precio_unitario * self.cantidad) - self.descuento_linea
        else:
            self.subtotal = Decimal('0.00') # Asegurar un valor por defecto
        
        super().save(*args, **kwargs)


# Señales para actualizar totales automáticamente
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver

@receiver(post_save, sender=DetalleVentaServicio)
@receiver(post_delete, sender=DetalleVentaServicio)
def actualizar_total_venta(sender, instance, **kwargs):
    """Actualiza el total de la venta cuando se modifican los detalles"""
    if hasattr(instance, 'venta') and instance.venta:
        venta = instance.venta
        total_detalles = sum(detalle.subtotal for detalle in venta.detalles.all())
        
        # Actualizar el total de la venta principal y la comisión
        venta.total = total_detalles - venta.descuento # Considerar el descuento general de la venta
        if venta.porcentaje_comision is not None and venta.total is not None:
            venta.comision_manicurista = (venta.total * venta.porcentaje_comision) / 100
        
        venta.save(update_fields=['total', 'comision_manicurista'])

@receiver(m2m_changed, sender=VentaServicio.citas.through)
def sincronizar_fecha_con_citas(sender, instance, action, **kwargs):
    """Sincronizar fecha de venta cuando se modifican las citas asociadas"""
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.sincronizar_con_citas()
