from rest_framework import serializers
from .models import InsumoHasAbastecimiento
from api.insumos.models import Insumo
from api.insumos.serializers import InsumoSerializer


class InsumoHasAbastecimientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsumoHasAbastecimiento
        fields = ['id', 'insumo', 'cantidad']
        
    def validate_cantidad(self, value):
        # Validar que la cantidad sea positiva
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que cero")
        return value


class InsumoHasAbastecimientoDetailSerializer(serializers.ModelSerializer):
    insumo = InsumoSerializer(read_only=True)
    
    class Meta:
        model = InsumoHasAbastecimiento
        fields = ['id', 'insumo', 'cantidad']