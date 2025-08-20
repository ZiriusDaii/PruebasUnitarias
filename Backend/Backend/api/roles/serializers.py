from rest_framework import serializers
from .models import Permiso, Rol, RolHasPermiso


class PermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permiso
        fields = '__all__'
        
    def validate_nombre(self, value):
        # Validar que el nombre no esté vacío
        if not value.strip():
            raise serializers.ValidationError("El nombre del permiso no puede estar vacío")
        return value


class RolHasPermisoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolHasPermiso
        fields = ['id', 'rol', 'permiso']


class RolSerializer(serializers.ModelSerializer):
    permisos_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Permiso.objects.all(),
        source='permisos',
        required=False,
        write_only=True
    )
    
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'estado', 'permisos_ids', 'created_at', 'updated_at']
        
    def validate_nombre(self, value):
        # Validar que el nombre no esté vacío
        if not value.strip():
            raise serializers.ValidationError("El nombre del rol no puede estar vacío")
        return value
    
    def create(self, validated_data):
        permisos = validated_data.pop('permisos', [])
        rol = Rol.objects.create(**validated_data)
        
        for permiso in permisos:
            RolHasPermiso.objects.create(rol=rol, permiso=permiso)
        
        return rol
    
    def update(self, instance, validated_data):
        permisos = validated_data.pop('permisos', None)
        instance = super().update(instance, validated_data)
        
        if permisos is not None:
            # Eliminar todas las relaciones existentes
            RolHasPermiso.objects.filter(rol=instance).delete()
            # Crear las nuevas relaciones
            for permiso in permisos:
                RolHasPermiso.objects.create(rol=instance, permiso=permiso)
        
        return instance
        


class RolDetailSerializer(serializers.ModelSerializer):
    permisos = PermisoSerializer(many=True, read_only=True)
    
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'estado', 'permisos', 'created_at', 'updated_at']