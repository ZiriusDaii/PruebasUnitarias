from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from api.base.base import BaseModel
from api.insumos.models import Insumo
from api.proveedores.models import Proveedor
import datetime

class Compra(BaseModel):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('finalizada', 'Finalizada'),
        ('anulada', 'Anulada'),
    ]
    
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de compra")
    proveedor = models.ForeignKey(
        Proveedor, 
        on_delete=models.CASCADE, 
        related_name='compras',
        verbose_name="Proveedor"
    )
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='finalizada',
        verbose_name="Estado"
    )
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    total = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Total"
    )
    # Campo para el motivo de anulación (sin fecha de anulación)
    motivo_anulacion = models.TextField(blank=True, null=True, verbose_name="Motivo de Anulación")
    
    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ['-fecha']
    
    def __str__(self):
        proveedor_nombre = getattr(self.proveedor, 'nombre', None) or getattr(self.proveedor, 'nombre_empresa', 'Sin nombre')
        return f"Compra #{self.id} - {proveedor_nombre} - {self.fecha.strftime('%d/%m/%Y')}"
    
    def calcular_total(self):
        """Calcula el total de la compra basado en los detalles"""
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.total = total
        self.save()
        return total


class DetalleCompra(BaseModel):
    compra = models.ForeignKey(
        Compra, 
        on_delete=models.CASCADE, 
        related_name='detalles',
        verbose_name="Compra"
    )
    insumo = models.ForeignKey(
        Insumo, 
        on_delete=models.CASCADE,
        verbose_name="Insumo"
    )
    cantidad = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],  # Cantidad mínima 1
        verbose_name="Cantidad"
    )
    precio_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio unitario"
    )
    
    class Meta:
        verbose_name = "Detalle de compra"
        verbose_name_plural = "Detalles de compra"
        unique_together = ['compra', 'insumo']
    
    def __str__(self):
        insumo_nombre = getattr(self.insumo, 'nombre', 'Sin nombre')
        return f"{insumo_nombre} - {self.cantidad} x {self.precio_unitario}"
    
    @property
    def subtotal(self):
        """Calcula el subtotal del detalle"""
        return self.cantidad * self.precio_unitario
    
    def save(self, *args, **kwargs):
        # Validar cantidad mínima antes de guardar
        if self.cantidad < 1:
            raise ValueError("La cantidad debe ser mayor a 0")
        super().save(*args, **kwargs)
        # Recalcular el total de la compra
        self.compra.calcular_total()
