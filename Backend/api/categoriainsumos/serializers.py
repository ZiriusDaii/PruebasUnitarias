from rest_framework import serializers
from .models import CategoriaInsumo


class CategoriaInsumoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaInsumo
        fields = '__all__'
        
    def validate_nombre(self, value):
        # Validar que el nombre no esté vacío
        if not value.strip():
            raise serializers.ValidationError("El nombre de la categoría no puede estar vacío")
        return value
    
    def validate(self, data):
        # Validar que no exista otra categoría con el mismo nombre (ignorando mayúsculas/minúsculas)
        nombre = data.get('nombre', '').strip().lower()
        queryset = CategoriaInsumo.objects.filter(nombre__iexact=nombre)
        
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise serializers.ValidationError({"nombre": "Ya existe una categoría con este nombre"})
        
        return data