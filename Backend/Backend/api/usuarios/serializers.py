from rest_framework import serializers
from api.usuarios.models import Usuario
from api.roles.models import Rol
from api.roles.serializers import RolSerializer

class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,  # No requerido para permitir generación automática
        allow_blank=True,  # Permitir campo vacío
        style={'input_type': 'password'},
        min_length=6,
        max_length=20
    )
    contraseña_generada = serializers.CharField(read_only=True)  # Para mostrar la contraseña generada en la respuesta

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre', 'tipo_documento', 'documento', 'direccion', 
            'celular', 'correo_electronico', 'rol', 'is_active', 
            'is_staff', 'date_joined', 'password', 'contraseña_temporal',
            'debe_cambiar_contraseña', 'contraseña_generada',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'contraseña_temporal': {'write_only': True},  # No mostrar la contraseña encriptada
            'is_staff': {'read_only': True},
            'date_joined': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
        }
        
    def validate_nombre(self, value):
        if not value.strip():
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        if len(value.strip()) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if len(value.strip()) > 50:
            raise serializers.ValidationError("El nombre no puede exceder los 50 caracteres.")
        return value.strip()
    
    def validate_documento(self, value):
        if not value.strip():
            raise serializers.ValidationError("El documento no puede estar vacío.")
        
        # Verificar que no exista ya otro usuario con este documento (excluyendo el actual en edición)
        usuario_query = Usuario.objects.filter(documento=value.strip())
        
        # Si estamos editando (self.instance existe), excluir el usuario actual
        if self.instance:
            usuario_query = usuario_query.exclude(id=self.instance.id)
        
        if usuario_query.exists():
            raise serializers.ValidationError("Ya existe un usuario con este número de documento")
        
        return value.strip()
    
    def validate_correo_electronico(self, value):
        if not value.strip():
            raise serializers.ValidationError("El correo electrónico no puede estar vacío.")
        if len(value.strip()) > 100:
            raise serializers.ValidationError("El correo no puede exceder los 100 caracteres.")
        
        # Verificar que no exista ya otro usuario con este correo (excluyendo el actual en edición)
        usuario_query = Usuario.objects.filter(correo_electronico=value.strip().lower())
        
        # Si estamos editando (self.instance existe), excluir el usuario actual
        if self.instance:
            usuario_query = usuario_query.exclude(id=self.instance.id)
        
        if usuario_query.exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo electrónico")
        
        return value.strip().lower()

    def validate_celular(self, value):
        if not value.strip():
            raise serializers.ValidationError("El celular no puede estar vacío.")
        # Validar formato de celular colombiano
        import re
        if not re.match(r'^[3][0-9]{9}$', value.strip()):
            raise serializers.ValidationError("El celular debe comenzar con 3 y tener 10 dígitos.")
        return value.strip()

    def validate_direccion(self, value):
        if value and len(value.strip()) > 100:
            raise serializers.ValidationError("La dirección no puede exceder los 100 caracteres.")
        return value.strip() if value else value

    def validate_rol(self, value):
        if not value:
            raise serializers.ValidationError("Debe seleccionar un rol para el usuario.")
        return value

    def validate_password(self, value):
        # Solo validar si se proporciona una contraseña
        if value:
            if len(value) < 6:
                raise serializers.ValidationError("La contraseña debe tener al menos 6 caracteres.")
            if len(value) > 20:
                raise serializers.ValidationError("La contraseña no puede exceder los 20 caracteres.")
            
            # Validar que tenga al menos una mayúscula
            if not any(c.isupper() for c in value):
                raise serializers.ValidationError("La contraseña debe incluir al menos una mayúscula.")
            
            # Validar que tenga al menos un número
            if not any(c.isdigit() for c in value):
                raise serializers.ValidationError("La contraseña debe incluir al menos un número.")
            
            # Validar que tenga al menos un símbolo
            import re
            if not re.search(r'[!@#$%^&*]', value):
                raise serializers.ValidationError("La contraseña debe incluir al menos un símbolo (!@#$%^&*).")
        
        return value

    def create(self, validated_data):
        password_to_set = validated_data.pop('password', None)
        
        # Crear el usuario
        usuario = Usuario(**validated_data)
        
        # Si no se proporciona contraseña o está vacía, generar una temporal
        if not password_to_set or password_to_set.strip() == '':
            # Generar contraseña temporal
            contraseña_generada = usuario.generar_contraseña_temporal()
            usuario.set_password(contraseña_generada)
            # Agregar la contraseña generada para poder accederla en la vista
            usuario.contraseña_generada = contraseña_generada
        else:
            # Si se proporciona contraseña, usarla normalmente
            usuario.set_password(password_to_set)
        
        usuario.save()
        return usuario
    
    def update(self, instance, validated_data):
        password_to_set = validated_data.pop('password', None)
        
        # Actualizar los demás campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password_to_set:
            instance.set_password(password_to_set)
        
        instance.save()
        return instance

class UsuarioDetailSerializer(serializers.ModelSerializer):
    rol = RolSerializer(read_only=True)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre', 'tipo_documento', 'documento', 'direccion',
            'celular', 'correo_electronico', 'rol', 'is_active',
            'is_staff', 'date_joined', 'debe_cambiar_contraseña',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

# NUEVOS SERIALIZERS para contraseña temporal
class CambiarContraseñaUsuarioSerializer(serializers.Serializer):
    """Serializer para cambiar la contraseña temporal"""
    contraseña_temporal = serializers.CharField()
    nueva_contraseña = serializers.CharField(min_length=6)
    confirmar_contraseña = serializers.CharField()
    
    def validate(self, data):
        if data['nueva_contraseña'] != data['confirmar_contraseña']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return data
    
    def validate_nueva_contraseña(self, value):
        # Validaciones básicas de contraseña
        if len(value) < 6:
            raise serializers.ValidationError("La contraseña debe tener al menos 6 caracteres")
        
        if value.isdigit():
            raise serializers.ValidationError("La contraseña no puede ser solo números")
        
        if value.lower() == value:
            raise serializers.ValidationError("La contraseña debe contener al menos una mayúscula")
        
        return value

class LoginUsuarioSerializer(serializers.Serializer):
    """Serializer para login de usuarios"""
    correo_electronico = serializers.EmailField()
    contraseña = serializers.CharField()
