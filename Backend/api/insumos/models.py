from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from api.base.base import BaseModel
from api.categoriainsumos.models import CategoriaInsumo


class Insumo(BaseModel):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    ]
    
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    cantidad = models.PositiveIntegerField(default=0, verbose_name="Cantidad")
    estado = models.CharField(
        max_length=10, 
        choices=ESTADO_CHOICES, 
        default='activo',
        verbose_name="Estado"
    )
    categoria_insumo = models.ForeignKey(
        CategoriaInsumo, 
        on_delete=models.CASCADE, 
        related_name='insumos',
        verbose_name="Categoría"
    )
    
    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
