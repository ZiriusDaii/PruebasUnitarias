from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from api.base.base import BaseModel
from api.usuarios.models import Usuario
from api.roles.models import Rol
import secrets
import string


class Manicurista(BaseModel):
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    
    TIPO_DOCUMENTO_CHOICES = (
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
    )
    
    ESPECIALIDADES_CHOICES = (
        ('Manicure Clásica', 'Manicure Clásica'),
        ('Manicure Francesa', 'Manicure Francesa'),
        ('Manicure Gel', 'Manicure Gel'),
        ('Manicure Acrílica', 'Manicure Acrílica'),
        ('Nail Art', 'Nail Art'),
        ('Pedicure', 'Pedicure'),
        ('Uñas Esculpidas', 'Uñas Esculpidas'),
        ('Decoración de Uñas', 'Decoración de Uñas'),
        ('Manicure Express', 'Manicure Express'),
        ('Tratamientos de Cutículas', 'Tratamientos de Cutículas'),
    )
    
    # CAMBIADO: Un solo campo nombre en lugar de nombres y apellidos
    nombre = models.CharField(max_length=200, help_text="Nombre completo de la manicurista")
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES, null=True, blank=True)
    numero_documento = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    # NUEVO: Campo de especialidad
    especialidad = models.CharField(max_length=50, null=True, blank=True, choices=ESPECIALIDADES_CHOICES, help_text="Especialidad principal de la manicurista")
    
    celular_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="El número de celular debe estar en formato: '+999999999'. Hasta 15 dígitos permitidos."
    )
    celular = models.CharField(validators=[celular_regex], max_length=15, null=True, blank=True)
    correo = models.EmailField(unique=True, null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    contraseña_temporal = models.CharField(max_length=128, null=True, blank=True)
    debe_cambiar_contraseña = models.BooleanField(default=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')
    disponible = models.BooleanField(default=True)
    
    # Relación con Usuario
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, null=True, blank=True, related_name='manicurista')
    
    # NUEVAS PROPIEDADES para compatibilidad con código existente
    @property
    def nombres(self):
        """Retorna la primera parte del nombre para compatibilidad"""
        partes = self.nombre.split(' ', 1)
        return partes[0] if partes else ''
    
    @property
    def apellidos(self):
        """Retorna la segunda parte del nombre para compatibilidad"""
        partes = self.nombre.split(' ', 1)
        return partes[1] if len(partes) > 1 else ''
    
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
        print(f"Cambiando contraseña para manicurista {self.id}")
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
        """Crea un usuario en la tabla usuarios con rol de manicurista"""
        try:
            # Buscar el rol de manicurista
            rol_manicurista = Rol.objects.get(nombre__iexact='manicurista')
        except Rol.DoesNotExist:
            # Si no existe, crearlo
            rol_manicurista = Rol.objects.create(
                nombre='Manicurista',
                estado='activo'
            )
            print(f"Rol 'Manicurista' creado con ID: {rol_manicurista.id}")
        
        # Crear el usuario relacionado
        usuario = Usuario.objects.create(
            nombre=self.nombre,  # CAMBIADO: usar el nombre completo
            tipo_documento=self.tipo_documento,
            documento=self.numero_documento,
            direccion=self.direccion,
            celular=self.celular,
            correo_electronico=self.correo,
            rol=rol_manicurista,
            is_active=True,
            is_staff=False
        )
        
        # Establecer la misma contraseña temporal
        if self.contraseña_temporal:
            usuario.password = self.contraseña_temporal
            usuario.save(update_fields=['password'])
        
        # Relacionar con la manicurista
        self.usuario = usuario
        self.save(update_fields=['usuario'])
        
        print(f"Usuario creado para manicurista {self.nombre}: {usuario.id}")
        return usuario
    
    def __str__(self):
        if self.numero_documento:
            return f"{self.nombre} - {self.numero_documento} ({self.especialidad})"
        return f"{self.nombre} ({self.especialidad})"