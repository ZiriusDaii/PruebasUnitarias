from rest_framework import serializers
from .models import CompraHasInsumo
from api.insumos.serializers import InsumoSerializer


class CompraHasInsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompraHasInsumo
        fields = ['id', 'compra', 'insumo', 'cantidad', 'precio_unitario', 'subtotal']
        read_only_fields = ['subtotal']
        
    def validate_cantidad(self, value):
        # Validar que la cantidad sea positiva
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor que cero")
        return value
    
    def validate_precio_unitario(self, value):
        # Validar que el precio unitario sea positivo
        if value <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor que cero")
        return value


class CompraHasInsumoDetailSerializer(serializers.ModelSerializer):
    insumo = InsumoSerializer(read_only=True)
    
    class Meta:
        model = CompraHasInsumo
        fields = ['id', 'compra', 'insumo', 'cantidad', 'precio_unitario', 'subtotal']
