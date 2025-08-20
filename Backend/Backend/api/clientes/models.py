from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from api.base.base import BaseModel
from api.usuarios.models import Usuario
from api.roles.models import Rol
import secrets
import string


class Cliente(BaseModel):
    TIPO_DOCUMENTO_CHOICES = (
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
    )
    
    GENERO_CHOICES = (
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('NB', 'No binario'),
        ('O', 'Otro'),
        ('N', 'Prefiero no decirlo'),
    )
    
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES)
    documento = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    celular_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="El número de celular debe estar en formato: '+999999999'. Hasta 15 dígitos permitidos."
    )
    celular = models.CharField(validators=[celular_regex], max_length=15)
    correo_electronico = models.EmailField()
    direccion = models.CharField(max_length=200)
    genero = models.CharField(max_length=2, choices=GENERO_CHOICES, default='M')
    estado = models.BooleanField(default=True)
    
    # NUEVOS CAMPOS para contraseñas temporales
    contraseña_temporal = models.CharField(max_length=128, null=True, blank=True)
    debe_cambiar_contraseña = models.BooleanField(default=True)
    
    # Relación con Usuario
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, null=True, blank=True, related_name='cliente')
    
    def generar_contraseña_temporal(self):
        """Genera una contraseña temporal aleatoria de 8 caracteres"""
        caracteres = string.ascii_letters + string.digits
        contraseña = ''.join(secrets.choice(caracteres) for i in range(8))
        self.contraseña_temporal = make_password(contraseña)
        self.debe_cambiar_contraseña = True
        return contraseña  # Retorna la contraseña sin encriptar para enviarla por correo
    
    def verificar_contraseña_temporal(self, contraseña):
        """Verifica si la contraseña temporal coincide"""
        from django.contrib.auth.hashers import check_password
        return check_password(contraseña, self.contraseña_temporal)
    
    def cambiar_contraseña(self, nueva_contraseña):
        """Cambia la contraseña temporal por una nueva"""
        print(f"Cambiando contraseña para cliente {self.id}")
        self.contraseña_temporal = make_password(nueva_contraseña)
        self.debe_cambiar_contraseña = False
        self.save(update_fields=['contraseña_temporal', 'debe_cambiar_contraseña'])
        print(f"Contraseña cambiada. debe_cambiar_contraseña: {self.debe_cambiar_contraseña}")
        
        # También actualizar la contraseña del usuario relacionado si existe
        if self.usuario:
            self.usuario.set_password(nueva_contraseña)
            self.usuario.save(update_fields=['password'])
            print(f"Contraseña del usuario {self.usuario.id} también actualizada")
    
    def crear_usuario_relacionado(self):
        """Crea un usuario en la tabla usuarios con rol de cliente"""
        try:
            # Buscar el rol de cliente
            rol_cliente = Rol.objects.get(nombre__iexact='cliente')
        except Rol.DoesNotExist:
            # Si no existe, crearlo
            rol_cliente = Rol.objects.create(
                nombre='Cliente',
                estado='activo'
            )
            print(f"Rol 'Cliente' creado con ID: {rol_cliente.id}")
        
        # Crear el usuario relacionado
        usuario = Usuario.objects.create(
            nombre=self.nombre,
            tipo_documento=self.tipo_documento,
            documento=self.documento,
            direccion=self.direccion,
            celular=self.celular,
            correo_electronico=self.correo_electronico,
            rol=rol_cliente,
            is_active=True,
            is_staff=False
        )
        
        # Establecer la misma contraseña temporal
        if self.contraseña_temporal:
            usuario.password = self.contraseña_temporal
            usuario.save(update_fields=['password'])
        
        # Relacionar con el cliente
        self.usuario = usuario
        self.save(update_fields=['usuario'])
        
        print(f"Usuario creado para cliente {self.nombre}: {usuario.id}")
        return usuario
    
    def __str__(self):
        return f"{self.nombre} ({self.documento})"
