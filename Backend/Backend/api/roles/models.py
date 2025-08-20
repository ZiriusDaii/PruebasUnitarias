from django.db import models
from api.base.base import BaseModel


class Permiso(BaseModel):
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    
    nombre = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Permisos"


class Rol(BaseModel):
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    
    nombre = models.CharField(max_length=50, unique=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    permisos = models.ManyToManyField(Permiso, through='RolHasPermiso')
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name_plural = "Roles"


class RolHasPermiso(BaseModel):
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('rol', 'permiso')
        verbose_name = "Rol - Permiso"
        verbose_name_plural = "Roles - Permisos"