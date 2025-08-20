from django.db import models
from django.core.validators import MinValueValidator
from api.base.base import BaseModel
from api.insumos.models import Insumo
from api.compras.models import Compra

class CompraHasInsumo(BaseModel):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='insumos')
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    
    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.compra.id} - {self.insumo.nombre} ({self.cantidad})"
    
    class Meta:
        verbose_name = "Compra - Insumo"
        verbose_name_plural = "Compras - Insumos"