from django.db import models
from api.base.base import BaseModel


class CategoriaInsumo(BaseModel):
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    
    nombre = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Categorías de Insumos"