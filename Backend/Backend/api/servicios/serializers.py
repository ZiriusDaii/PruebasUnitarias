from rest_framework import serializers
from decimal import Decimal, InvalidOperation
from .models import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    precio = serializers.CharField()  # Fuerza DRF a aceptarlo como string y luego validarlo
    duracion_formateada = serializers.ReadOnlyField()  # Campo calculado para mostrar duración formateada

    class Meta:
        model = Servicio
        fields = '__all__'

    def validate_nombre(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre del servicio no puede estar vacío.")
        
        # Verificar duplicados excluyendo la instancia actual en caso de edición
        queryset = Servicio.objects.filter(nombre__iexact=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        
        if queryset.exists():
            raise serializers.ValidationError("Ya existe un servicio con este nombre.")
        
        return value

    def validate_precio(self, value):
        try:
            value = Decimal(str(value))
        except (TypeError, ValueError, InvalidOperation):
            raise serializers.ValidationError("El precio debe ser un número válido.")
    
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor que cero.")
        
        if value > 999999:
            raise serializers.ValidationError("El precio no puede exceder $999,999.")
    
        return value

    def validate_descripcion(self, value):
        value = value.strip()
        if len(value) < 10:
            raise serializers.ValidationError("La descripción debe tener al menos 10 caracteres.")
        if len(value) > 500:
            raise serializers.ValidationError("La descripción no debe superar los 500 caracteres.")
        return value

    def validate_duracion(self, value):
        try:
            duracion = int(value)
        except (TypeError, ValueError):
            raise serializers.ValidationError("La duración debe ser un número entero.")
        
        if duracion < 1:
            raise serializers.ValidationError("La duración debe ser al menos 1 minuto.")
        
        if duracion > 600:
            raise serializers.ValidationError("La duración no puede exceder 600 minutos (10 horas).")
        
        return duracion

    def validate_imagen(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("La URL de la imagen es demasiado larga.")
        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        # Validación cruzada si es necesaria
        precio = data.get('precio')
        duracion = data.get('duracion')
        
        # Ejemplo: servicios muy cortos no deberían ser muy caros
        if precio and duracion:
            try:
                precio_decimal = Decimal(str(precio))
                duracion_int = int(duracion)
                
                # Precio por minuto no debería exceder cierto límite (opcional)
                precio_por_minuto = precio_decimal / duracion_int
                if precio_por_minuto > 10000:  # 10,000 COP por minuto
                    raise serializers.ValidationError({
                        'precio': 'El precio por minuto parece excesivo. Revise el precio y la duración.'
                    })
            except (TypeError, ValueError, InvalidOperation):
                pass  # Las validaciones individuales ya manejan estos errores
        
        return data
