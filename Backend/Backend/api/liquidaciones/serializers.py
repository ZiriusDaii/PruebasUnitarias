from rest_framework import serializers
from .models import Liquidacion
from api.manicuristas.models import Manicurista
from api.manicuristas.serializers import ManicuristaSerializer
from api.citas.models import Cita
from django.db.models import Sum
from datetime import datetime
from decimal import Decimal


class LiquidacionSerializer(serializers.ModelSerializer):
    # Campos calculados de solo lectura (propiedades del modelo)
    total_servicios_completados = serializers.ReadOnlyField()
    total_a_pagar = serializers.ReadOnlyField()
    cantidad_servicios_completados = serializers.ReadOnlyField()
    citascompletadas = serializers.ReadOnlyField()
    
    # Campos calculados para citas completadas
    total_citas_completadas = serializers.SerializerMethodField()
    cantidad_citas_completadas = serializers.SerializerMethodField()
    comision_50_porciento = serializers.SerializerMethodField()

    class Meta:
        model = Liquidacion
        fields = '__all__'
    
    def get_total_citas_completadas(self, obj):
        """Calcular total de citas completadas en el período"""
        try:
            total = Cita.objects.filter(
                manicurista=obj.manicurista,
                fecha_cita__range=(obj.fecha_inicio, obj.fecha_final),
                estado='finalizada'
            ).aggregate(total=Sum('precio_total'))['total'] or Decimal('0.00')
            return float(total)
        except Exception:
            return 0.0
    
    def get_cantidad_citas_completadas(self, obj):
        """Contar citas completadas en el período"""
        try:
            return Cita.objects.filter(
                manicurista=obj.manicurista,
                fecha_cita__range=(obj.fecha_inicio, obj.fecha_final),
                estado='finalizada'
            ).count()
        except Exception:
            return 0
    
    def get_comision_50_porciento(self, obj):
        """Calcular el 50% de las citas completadas"""
        total_citas = self.get_total_citas_completadas(obj)
        return total_citas * 0.5
        
    def validate(self, data):
        # Validar duplicados por manicurista y rango de fechas
        queryset = Liquidacion.objects.filter(
            manicurista=data['manicurista'],
            fecha_inicio=data['fecha_inicio'],
            fecha_final=data['fecha_final']
        )
        
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
            
        if queryset.exists():
            raise serializers.ValidationError("Ya existe una liquidación para esta manicurista en ese rango de fechas.")

        # Validar valores no negativos
        if data['valor'] < 0:
            raise serializers.ValidationError("El valor no puede ser negativo")
        if data['bonificacion'] < 0:
            raise serializers.ValidationError("La bonificación no puede ser negativa")
        
        return data


class LiquidacionDetailSerializer(serializers.ModelSerializer):
    manicurista = ManicuristaSerializer(read_only=True)
    
    # Campos calculados del modelo
    total_servicios_completados = serializers.ReadOnlyField()
    total_a_pagar = serializers.ReadOnlyField()
    cantidad_servicios_completados = serializers.ReadOnlyField()
    citascompletadas = serializers.ReadOnlyField()
    
    # Campos para citas completadas
    total_citas_completadas = serializers.SerializerMethodField()
    cantidad_citas_completadas = serializers.SerializerMethodField()
    comision_50_porciento = serializers.SerializerMethodField()
    
    class Meta:
        model = Liquidacion
        fields = '__all__'
    
    def get_total_citas_completadas(self, obj):
        """Calcular total de citas completadas en el período"""
        try:
            total = Cita.objects.filter(
                manicurista=obj.manicurista,
                fecha_cita__range=(obj.fecha_inicio, obj.fecha_final),
                estado='finalizada'
            ).aggregate(total=Sum('precio_total'))['total'] or Decimal('0.00')
            return float(total)
        except Exception:
            return 0.0
    
    def get_cantidad_citas_completadas(self, obj):
        """Contar citas completadas en el período"""
        try:
            return Cita.objects.filter(
                manicurista=obj.manicurista,
                fecha_cita__range=(obj.fecha_inicio, obj.fecha_final),
                estado='finalizada'
            ).count()
        except Exception:
            return 0
    
    def get_comision_50_porciento(self, obj):
        """Calcular el 50% de las citas completadas"""
        total_citas = self.get_total_citas_completadas(obj)
        return total_citas * 0.5


class LiquidacionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer específico para crear liquidaciones con cálculo automático de valor basado en citas
    """
    # Campo opcional para auto-calcular valor basado en citas completadas
    calcular_valor_automatico = serializers.BooleanField(write_only=True, required=False, default=True)
    
    class Meta:
        model = Liquidacion
        fields = ['manicurista', 'fecha_inicio', 'fecha_final', 'valor', 'bonificacion', 'calcular_valor_automatico']
    
    def create(self, validated_data):
        """
        Crear liquidación con cálculo automático de valor si se solicita
        """
        calcular_automatico = validated_data.pop('calcular_valor_automatico', True)
        
        # Si se solicita cálculo automático y no se proporciona valor, calcularlo
        if calcular_automatico and validated_data.get('valor', 0) == 0:
            manicurista = validated_data['manicurista']
            fecha_inicio = validated_data['fecha_inicio']
            fecha_final = validated_data['fecha_final']
            
            # Calcular total de citas completadas
            try:
                total_citas = Cita.objects.filter(
                    manicurista=manicurista,
                    fecha_cita__range=(fecha_inicio, fecha_final),
                    estado='finalizada'
                ).aggregate(total=Sum('precio_total'))['total'] or Decimal('0.00')
                
                # Calcular el 50% de comisión y redondear a 2 decimales
                comision = (total_citas * Decimal('0.5')).quantize(Decimal('0.01'))
                validated_data['valor'] = comision
            except Exception:
                validated_data['valor'] = Decimal('0.00')
        
        return Liquidacion.objects.create(**validated_data)


class LiquidacionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar liquidaciones con opción de recalcular
    """
    recalcular_citas_completadas = serializers.BooleanField(write_only=True, required=False, default=False)
    recalcular_valor_citas = serializers.BooleanField(write_only=True, required=False, default=False)
    
    class Meta:
        model = Liquidacion
        fields = ['valor', 'bonificacion', 'recalcular_citas_completadas', 'recalcular_valor_citas']
    
    def update(self, instance, validated_data):
        recalcular_citas = validated_data.pop('recalcular_citas_completadas', False)
        recalcular_valor = validated_data.pop('recalcular_valor_citas', False)
        
        # Actualizar campos normales
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Recalcular citas completadas si se solicita
        if recalcular_citas:
            instance.calcular_citas_completadas()
        
        # Recalcular valor basado en citas si se solicita
        if recalcular_valor:
            try:
                total_citas = Cita.objects.filter(
                    manicurista=instance.manicurista,
                    fecha_cita__range=(instance.fecha_inicio, instance.fecha_final),
                    estado='finalizada'
                ).aggregate(total=Sum('precio_total'))['total'] or Decimal('0.00')
            
            # Calcular el 50% de comisión y redondear a 2 decimales
                comision = (total_citas * Decimal('0.5')).quantize(Decimal('0.01'))
                instance.valor = comision
            except Exception:
                # En caso de error, mantener el valor actual
                pass
        
        instance.save()
        return instance
