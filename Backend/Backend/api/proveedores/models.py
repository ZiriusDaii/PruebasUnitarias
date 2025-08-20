from django.db import models
from django.core.validators import RegexValidator
from api.base.base import BaseModel


class Proveedor(BaseModel):
    TIPO_PERSONA_CHOICES = (
        ('natural', 'Persona Natural'),
        ('juridica', 'Persona Jurídica'),
    )
    
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA_CHOICES)
    nombre_empresa = models.CharField(max_length=100)
    nit = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    correo_electronico = models.EmailField()
    celular_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="El número de celular debe estar en formato: '+999999999'. Hasta 15 dígitos permitidos."
    )
    celular = models.CharField(validators=[celular_regex], max_length=15)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    
    def __str__(self):
        return f"{self.nombre_empresa} ({self.nit})"