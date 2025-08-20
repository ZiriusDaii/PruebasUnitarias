# api/models/usuariosModel.py
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from api.base.base import BaseModel # Asegúrate que la importación de BaseModel sea correcta
from api.roles.models import Rol # Asegúrate que la importación de Rol sea correcta
import secrets
import string


class UsuarioManager(BaseUserManager):
    def _create_user(self, correo_electronico, password, is_staff, is_superuser, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es obligatorio')
        
        correo_electronico = self.normalize_email(correo_electronico)
        # El rol debe ser una instancia de Rol o un ID válido que el serializador/vista pueda manejar.
        # Si se pasa un rol_id, la lógica de creación (usualmente en el serializador o vista) debe manejar la asignación.
        rol = extra_fields.pop('rol', None)
        if rol is None and not is_superuser: # Un superusuario podría no tener un rol específico inicialmente o tener uno por defecto
             # Opcional: Si todos los usuarios deben tener un rol, incluso al crearlos programáticamente.
             # raise ValueError('El campo rol es obligatorio para los usuarios.')
             pass


        user = self.model(
            correo_electronico=correo_electronico,
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra_fields
        )
        if rol: # Si se proporcionó un rol (ya sea instancia o ID que se resolverá luego)
            user.rol = rol

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, correo_electronico, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(correo_electronico, password, **extra_fields)
    
    def create_superuser(self, correo_electronico, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        
        # Asignar un rol por defecto para superusuarios si es necesario, o asegurar que se provea uno.
        # if 'rol' not in extra_fields or not extra_fields['rol']:
        # try:
        #         admin_rol = Rol.objects.get(nombre='Administrador') # O un rol específico para superusuarios
        #         extra_fields['rol'] = admin_rol
        # except Rol.DoesNotExist:
        # raise ValueError('Rol de administrador no encontrado para superusuario.')
        
        return self._create_user(correo_electronico, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin, BaseModel):
    TIPO_DOCUMENTO_CHOICES = (
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
    )
    
    nombre = models.CharField(max_length=100)
    tipo_documento = models.CharField(max_length=2, choices=TIPO_DOCUMENTO_CHOICES)
    documento = models.CharField(max_length=20, unique=True)
    direccion = models.CharField(max_length=200, blank=True, null=True) # CAMBIO: Se hace opcional
    celular_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', # El regex original r'^\+?1?\d{9,15}$' está bien
        message="El número de celular debe estar en formato: '+999999999'. Hasta 15 dígitos permitidos."
    )
    celular = models.CharField(validators=[celular_regex], max_length=15)
    correo_electronico = models.EmailField(unique=True)
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT) # PROTECT es buena elección
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) # Permite acceso al admin de Django
    date_joined = models.DateTimeField(default=timezone.now) # auto_now_add=True es otra opción
    
    # NUEVOS CAMPOS para contraseña temporal
    contraseña_temporal = models.CharField(max_length=128, null=True, blank=True)
    debe_cambiar_contraseña = models.BooleanField(default=False)
    
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'correo_electronico'
    # REQUIRED_FIELDS para el comando createsuperuser.
    # 'rol' se añade si es un campo que siempre debe especificarse incluso para superusuarios,
    # aunque el manager podría asignarlo por defecto.
    REQUIRED_FIELDS = ['nombre', 'tipo_documento', 'documento', 'celular', 'rol'] 
    
    def __str__(self):
        return f"{self.nombre} ({self.correo_electronico})"

    def get_full_name(self):
        return self.nombre

    def get_short_name(self):
        return self.nombre
    
    # NUEVOS MÉTODOS para contraseña temporal
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
        print(f"Cambiando contraseña para usuario {self.id}")
        self.contraseña_temporal = make_password(nueva_contraseña)
        self.debe_cambiar_contraseña = False
        # También actualizar la contraseña principal del usuario
        self.set_password(nueva_contraseña)
        self.save(update_fields=['contraseña_temporal', 'debe_cambiar_contraseña', 'password'])
        print(f"Contraseña cambiada. debe_cambiar_contraseña: {self.debe_cambiar_contraseña}")
