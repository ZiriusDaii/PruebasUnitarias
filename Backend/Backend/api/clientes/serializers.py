from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from api.clientes.models import Cliente
from api.roles.models import Rol

Usuario = get_user_model()

class ClienteSerializer(serializers.ModelSerializer):
    contraseña_generada = serializers.CharField(read_only=True)  # Para mostrar la contraseña generada en la respuesta
    usuario_id = serializers.IntegerField(read_only=True, source='usuario.id')  # Para mostrar el ID del usuario creado
    
    class Meta:
        model = Cliente
        fields = '__all__'
        extra_kwargs = {
            'contraseña_temporal': {'write_only': True},  # No mostrar la contraseña encriptada
            'usuario': {'read_only': True},  # El usuario se crea automáticamente
        }
        
    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres")
        
        if len(value.strip()) > 100:
            raise serializers.ValidationError("El nombre no puede exceder los 100 caracteres")
        
        # Validar que solo contenga letras, espacios y caracteres especiales del español
        if not all(c.isalpha() or c.isspace() or c in 'áéíóúÁÉÍÓÚñÑ' for c in value):
            raise serializers.ValidationError("El nombre solo puede contener letras y espacios")
        
        return value.strip().title()  # Capitalizar nombre
    
    def validate_documento(self, value):
        if not value.strip():
            raise serializers.ValidationError("El documento no puede estar vacío")
        
        # ARREGLADO: Verificar que no exista ya en Usuario, excluyendo el usuario actual
        usuario_query = Usuario.objects.filter(documento=value.strip())
        
        # Si estamos editando (self.instance existe), excluir el usuario actual
        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario:
            usuario_query = usuario_query.exclude(id=self.instance.usuario.id)
        
        if usuario_query.exists():
            raise serializers.ValidationError("Ya existe un usuario con este número de documento")
        
        return value.strip()
    
    def validate_correo_electronico(self, value):
        if not value.strip():
            raise serializers.ValidationError("El correo electrónico no puede estar vacío")
        
        # ARREGLADO: Verificar que no exista ya en Usuario, excluyendo el usuario actual
        usuario_query = Usuario.objects.filter(correo_electronico=value.strip().lower())
        
        # Si estamos editando (self.instance existe), excluir el usuario actual
        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario:
            usuario_query = usuario_query.exclude(id=self.instance.usuario.id)
        
        if usuario_query.exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo electrónico")
        
        return value.strip().lower()

class RegistroClienteSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    tipo_documento = serializers.ChoiceField(choices=Cliente.TIPO_DOCUMENTO_CHOICES)
    documento = serializers.CharField(max_length=20)
    celular = serializers.CharField(max_length=15)
    correo_electronico = serializers.EmailField()
    direccion = serializers.CharField(max_length=200)
    genero = serializers.ChoiceField(choices=[
        ('M', 'Masculino'), 
        ('F', 'Femenino'), 
        ('NB', 'No binario'),
        ('O', 'Otro'),
        ('N', 'Prefiero no decirlo')
    ])
    estado = serializers.BooleanField(default=True)
    password = serializers.CharField(write_only=True, min_length=6, required=False, allow_blank=True)  # CAMBIADO: Opcional
    
    def validate_documento(self, value):
        if Cliente.objects.filter(documento=value).exists():
            raise serializers.ValidationError("Ya existe un cliente con este número de documento.")
        if Usuario.objects.filter(documento=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este número de documento.")
        return value
    
    def validate_correo_electronico(self, value):
        if Usuario.objects.filter(correo_electronico=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo electrónico.")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        try:
            rol_cliente = Rol.objects.get(nombre__iexact='cliente')
        except Rol.DoesNotExist:
            # Si no existe, crearlo
            rol_cliente = Rol.objects.create(
                nombre='Cliente',
                estado='activo'
            )
        
        # Extraer la contraseña (puede ser None o vacía)
        password = validated_data.pop('password', None)
        
        # Crear cliente primero
        cliente_data = {
            'nombre': validated_data['nombre'],
            'tipo_documento': validated_data['tipo_documento'],
            'documento': validated_data['documento'],
            'celular': validated_data['celular'],
            'correo_electronico': validated_data['correo_electronico'],
            'direccion': validated_data['direccion'],
            'genero': validated_data['genero'],
            'estado': validated_data.get('estado', True)
        }
        
        cliente = Cliente(**cliente_data)
        
        # NUEVA LÓGICA: Generar contraseña temporal si no se proporciona
        contraseña_generada = None
        if not password or password.strip() == "":
            # Generar contraseña temporal
            contraseña_generada = cliente.generar_contraseña_temporal()
            password_to_use = contraseña_generada
        else:
            # Usar la contraseña proporcionada
            password_to_use = password
            cliente.debe_cambiar_contraseña = False  # No necesita cambiar si la proporcionó
        
        # Guardar el cliente
        cliente.save()
        
        # Preparar datos para el usuario
        usuario_data = {
            'nombre': validated_data['nombre'],
            'tipo_documento': validated_data['tipo_documento'],
            'documento': validated_data['documento'],
            'direccion': validated_data['direccion'],
            'celular': validated_data['celular'],
            'correo_electronico': validated_data['correo_electronico'],
            'rol': rol_cliente,
            'is_active': True
        }
        
        try:
            # Crear el usuario con la contraseña
            usuario = Usuario.objects.create_user(
                correo_electronico=usuario_data['correo_electronico'],
                password=password_to_use,
                **{k: v for k, v in usuario_data.items() if k != 'correo_electronico'}
            )
            
            # Relacionar cliente con usuario
            cliente.usuario = usuario
            cliente.save(update_fields=['usuario'])
            
            # Agregar la contraseña generada para poder accederla en la vista
            if contraseña_generada:
                cliente.contraseña_generada = contraseña_generada
            
            return {
                'usuario': usuario,
                'cliente': cliente
            }
            
        except Exception as e:
            # Si falla la creación del usuario, eliminar el cliente para mantener consistencia
            cliente.delete()
            raise serializers.ValidationError(f"Error al crear el usuario: {str(e)}")


class CambiarContraseñaSerializer(serializers.Serializer):
    """Serializer para cambiar la contraseña temporal"""
    contraseña_temporal = serializers.CharField()
    nueva_contraseña = serializers.CharField(min_length=8)
    confirmar_contraseña = serializers.CharField()
    
    def validate(self, data):
        if data['nueva_contraseña'] != data['confirmar_contraseña']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return data
    
    def validate_nueva_contraseña(self, value):
        # Validaciones básicas de contraseña
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres")
        
        if value.isdigit():
            raise serializers.ValidationError("La contraseña no puede ser solo números")
        
        if value.lower() == value:
            raise serializers.ValidationError("La contraseña debe contener al menos una mayúscula")
        
        return value


class LoginClienteSerializer(serializers.Serializer):
    """Serializer para login de clientes"""
    documento = serializers.CharField()
    contraseña = serializers.CharField()
