from rest_framework import serializers
from .models import Manicurista
from api.usuarios.models import Usuario
from api.roles.models import Rol

class ManicuristaSerializer(serializers.ModelSerializer):
    contraseña_generada = serializers.CharField(read_only=True)  # Para mostrar la contraseña generada en la respuesta
    usuario_id = serializers.IntegerField(read_only=True, source='usuario.id')  # Para mostrar el ID del usuario creado
    
    # AGREGADO: Campos de compatibilidad para el frontend
    nombres = serializers.CharField(read_only=True)
    apellidos = serializers.CharField(read_only=True)
    
    class Meta:
        model = Manicurista
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
        
        if len(value.strip()) > 200:
            raise serializers.ValidationError("El nombre no puede exceder los 200 caracteres")
        
        # Validar que solo contenga letras, espacios y caracteres especiales del español
        if not all(c.isalpha() or c.isspace() or c in 'áéíóúÁÉÍÓÚñÑ' for c in value):
            raise serializers.ValidationError("El nombre solo puede contener letras y espacios")
        
        return value.strip().title()  # Capitalizar nombre
    
    def validate_especialidad(self, value):
        if not value.strip():
            raise serializers.ValidationError("La especialidad no puede estar vacía")
        
        # Verificar que la especialidad esté en las opciones válidas
        especialidades_validas = [choice[0] for choice in Manicurista.ESPECIALIDADES_CHOICES]
        if value not in especialidades_validas:
            raise serializers.ValidationError("Especialidad no válida")
        
        return value
    
    def validate_numero_documento(self, value):
        if not value.strip():
            raise serializers.ValidationError("El número de documento no puede estar vacío")
        
        # Obtener el tipo de documento del contexto de validación
        tipo_documento = self.initial_data.get('tipo_documento', 'CC')
        
        # Validar según el tipo de documento
        if tipo_documento == 'CC':
            if not value.isdigit() or len(value) < 6 or len(value) > 10:
                raise serializers.ValidationError("Cédula inválida (6-10 dígitos)")
        elif tipo_documento == 'TI':
            if not value.isdigit() or len(value) < 6 or len(value) > 10:
                raise serializers.ValidationError("TI inválida (6-10 dígitos)")
        elif tipo_documento == 'CE':
            if len(value) < 6 or len(value) > 15:
                raise serializers.ValidationError("CE inválida (6-15 caracteres alfanuméricos)")
        elif tipo_documento == 'PP':
            if len(value) < 8 or len(value) > 12:
                raise serializers.ValidationError("Pasaporte inválido (8-12 caracteres alfanuméricos)")
        
        # ARREGLADO: Verificar que no exista ya en Usuario, excluyendo el usuario actual
        usuario_query = Usuario.objects.filter(documento=value.strip())
        
        # Si estamos editando (self.instance existe), excluir el usuario actual
        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario:
            usuario_query = usuario_query.exclude(id=self.instance.usuario.id)
        
        if usuario_query.exists():
            raise serializers.ValidationError("Ya existe un usuario con este número de documento")
        
        return value.strip()
    
    def validate_correo(self, value):
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
    
    def validate_direccion(self, value):
        if not value.strip():
            raise serializers.ValidationError("La dirección no puede estar vacía")
        return value.strip()
    
    def validate_celular(self, value):
        if not value.strip():
            raise serializers.ValidationError("El número de celular no puede estar vacío")
        
        # Validar formato colombiano (debe comenzar con 3 y tener 10 dígitos)
        if not value.isdigit() or len(value) != 10 or not value.startswith('3'):
            raise serializers.ValidationError("El celular debe comenzar con 3 y tener 10 dígitos")
        
        return value.strip()
    
    def create(self, validated_data):
        # Crear la manicurista primero
        manicurista = Manicurista(**validated_data)
        
        # Generar contraseña temporal
        contraseña_generada = manicurista.generar_contraseña_temporal()
        
        # Guardar la manicurista
        manicurista.save()
        
        # Crear el usuario relacionado automáticamente
        try:
            usuario_creado = manicurista.crear_usuario_relacionado()
            print(f"Usuario creado exitosamente: {usuario_creado.id}")
        except Exception as e:
            print(f"Error creando usuario relacionado: {e}")
            # Si falla la creación del usuario, eliminar la manicurista para mantener consistencia
            manicurista.delete()
            raise serializers.ValidationError(f"Error al crear usuario relacionado: {str(e)}")
        
        # Agregar la contraseña generada para poder accederla en la vista
        manicurista.contraseña_generada = contraseña_generada
        
        return manicurista
    
    def update(self, instance, validated_data):
        # Actualizar la manicurista
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar también el usuario relacionado si existe
        if hasattr(instance, 'usuario') and instance.usuario:
            usuario = instance.usuario
            usuario.nombre = instance.nombre  # CAMBIADO: usar el nombre completo
            usuario.tipo_documento = instance.tipo_documento
            usuario.documento = instance.numero_documento
            usuario.direccion = instance.direccion
            usuario.celular = instance.celular
            usuario.correo_electronico = instance.correo
            usuario.is_active = (instance.estado == 'activo')
            usuario.save()
            print(f"Usuario {usuario.id} actualizado junto con la manicurista")
        
        return instance


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


class LoginManicuristaSerializer(serializers.Serializer):
    """Serializer para login de manicuristas"""
    numero_documento = serializers.CharField()
    contraseña = serializers.CharField()