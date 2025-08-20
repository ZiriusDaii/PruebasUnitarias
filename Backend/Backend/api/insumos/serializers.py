from rest_framework import serializers
from .models import Insumo
from api.categoriainsumos.serializers import CategoriaInsumoSerializer


class InsumoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria_insumo.nombre', read_only=True)
    
    class Meta:
        model = Insumo
        fields = [
            'id', 'nombre', 'cantidad', 'estado', 
            'categoria_insumo', 'categoria_nombre',
            'created_at', 'updated_at'
        ]
    
    def validate_nombre(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("El nombre debe tener al menos 2 caracteres")
        return value
    
    def validate_cantidad(self, value):
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value


class InsumoDetailSerializer(serializers.ModelSerializer):
    categoria_insumo = CategoriaInsumoSerializer(read_only=True)
    
    class Meta:
        model = Insumo
        fields = [
            'id', 'nombre', 'cantidad', 'estado', 
            'categoria_insumo', 'created_at', 'updated_at'
        ]
