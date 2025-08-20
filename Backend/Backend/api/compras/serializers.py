from rest_framework import serializers
from decimal import Decimal
from django.db import transaction
# from django.utils import timezone  # Eliminar esta importación
from .models import Compra, DetalleCompra
from api.comprahasinsumos.models import CompraHasInsumo
from api.insumos.models import Insumo
from api.proveedores.models import Proveedor


class DetalleCompraSerializer(serializers.ModelSerializer):
    insumo_nombre = serializers.CharField(source='insumo.nombre', read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = DetalleCompra
        fields = ['id', 'insumo', 'insumo_nombre', 'cantidad', 'precio_unitario', 'subtotal']
    
    def validate_cantidad(self, value):
        if value < 1:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0. Mínimo: 1 unidad")
        return value
    
    def validate_precio_unitario(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor a 0")
        return value


class CompraSerializer(serializers.ModelSerializer):
    detalles = DetalleCompraSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.SerializerMethodField()
    fecha_formateada = serializers.SerializerMethodField()
    
    class Meta:
        model = Compra
        fields = [
            'id', 'fecha', 'fecha_formateada', 'proveedor', 'proveedor_nombre', 
            'estado', 'observaciones', 'total', 'detalles',
            'motivo_anulacion'  # Eliminar 'fecha_anulacion'
        ]
    
    def get_proveedor_nombre(self, obj):
        if hasattr(obj.proveedor, 'nombre'):
            return obj.proveedor.nombre
        elif hasattr(obj.proveedor, 'nombre_empresa'):
            return obj.proveedor.nombre_empresa
        else:
            return 'Sin nombre'
    
    def get_fecha_formateada(self, obj):
        return obj.fecha.strftime('%d/%m/%Y %H:%M')


class CompraCreateSerializer(serializers.ModelSerializer):
    detalles = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=True,
        allow_empty=False,
        error_messages={
            'required': 'Los detalles de la compra son requeridos.',
            'empty': 'Debe agregar al menos un insumo a la compra.'
        }
    )
    motivo_anulacion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Compra
        fields = ['proveedor', 'estado', 'observaciones', 'detalles', 'motivo_anulacion']
    
    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("Debe agregar al menos un insumo a la compra.")
        
        for i, detalle in enumerate(value):
            if 'insumo_id' not in detalle:
                raise serializers.ValidationError(f"El detalle {i+1} debe tener un insumo_id.")
            if 'cantidad' not in detalle:
                raise serializers.ValidationError(f"El detalle {i+1} debe tener una cantidad.")
            if 'precio_unitario' not in detalle:
                raise serializers.ValidationError(f"El detalle {i+1} debe tener un precio_unitario.")
            
            # Validar cantidad mínima
            cantidad = detalle.get('cantidad')
            if not isinstance(cantidad, int) or cantidad < 1:
                raise serializers.ValidationError(f"El detalle {i+1}: La cantidad debe ser un número entero mayor a 0. Mínimo: 1 unidad")
            
            # Validar precio mínimo
            precio = detalle.get('precio_unitario')
            if not isinstance(precio, (int, float, Decimal)) or precio <= 0:
                raise serializers.ValidationError(f"El detalle {i+1}: El precio unitario debe ser mayor a 0")
            
            # Validar que el insumo existe
            try:
                Insumo.objects.get(id=detalle['insumo_id'])
            except Insumo.DoesNotExist:
                raise serializers.ValidationError(f"El insumo con ID {detalle['insumo_id']} no existe.")
        
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        validated_data.pop('motivo_anulacion', None) # Asegurarse de que motivo_anulacion no se guarde en la creación si no es relevante
        compra = Compra.objects.create(**validated_data)
        
        # Lista para almacenar los movimientos de stock
        movimientos_stock = []
        
        for detalle_data in detalles_data:
            insumo_id = detalle_data.get('insumo_id')
            cantidad = detalle_data.get('cantidad')
            precio_unitario = detalle_data.get('precio_unitario')
            
            try:
                insumo = Insumo.objects.get(id=insumo_id)
                
                # Crear en DetalleCompra
                DetalleCompra.objects.create(
                    compra=compra,
                    insumo=insumo,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario
                )
                
                # Actualizar stock si la compra está finalizada
                if compra.estado == 'finalizada':
                    stock_anterior = insumo.cantidad
                    insumo.cantidad += cantidad
                    insumo.save()
                    
                    movimientos_stock.append({
                        'insumo': insumo.nombre,
                        'cantidad_agregada': cantidad,
                        'stock_anterior': stock_anterior,
                        'stock_nuevo': insumo.cantidad
                    })
                    
                    print(f"Stock actualizado: {insumo.nombre} - Cantidad agregada: {cantidad} - Nuevo stock: {insumo.cantidad}")
                
            except Insumo.DoesNotExist:
                # Si llegamos aquí, la validación falló
                pass
        
        # Calcular total
        compra.calcular_total()
        
        return compra
    
    @transaction.atomic
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        estado_anterior = instance.estado
        
        # Actualizar campos de la compra
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Si el estado cambia a 'anulada', guardar motivo
        if instance.estado == 'anulada' and estado_anterior != 'anulada':
            instance.motivo_anulacion = validated_data.get('motivo_anulacion', instance.motivo_anulacion)
            # instance.fecha_anulacion = timezone.now() # Eliminar esta línea
        elif instance.estado != 'anulada' and estado_anterior == 'anulada':
            # Si se revierte de anulada a otro estado, limpiar motivo
            instance.motivo_anulacion = None
            # instance.fecha_anulacion = None # Eliminar esta línea
        
        instance.save()
        
        # Si se está cambiando de finalizada a anulada, revertir stock
        if estado_anterior == 'finalizada' and instance.estado == 'anulada':
            # La reversión del stock ahora se maneja en el ViewSet
            pass
        
        # Eliminar detalles existentes
        instance.detalles.all().delete()
        
        # Lista para almacenar los movimientos de stock
        movimientos_stock = []
        
        for detalle_data in detalles_data:
            insumo_id = detalle_data.get('insumo_id')
            cantidad = detalle_data.get('cantidad')
            precio_unitario = detalle_data.get('precio_unitario')
            
            try:
                insumo = Insumo.objects.get(id=insumo_id)
                
                # Crear en DetalleCompra
                DetalleCompra.objects.create(
                    compra=instance,
                    insumo=insumo,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario
                )
                
                # Actualizar stock si la compra está finalizada
                if instance.estado == 'finalizada' and estado_anterior != 'finalizada':
                    stock_anterior = insumo.cantidad
                    insumo.cantidad += cantidad
                    insumo.save()
                    
                    movimientos_stock.append({
                        'insumo': insumo.nombre,
                        'cantidad_agregada': cantidad,
                        'stock_anterior': stock_anterior,
                        'stock_nuevo': insumo.cantidad
                    })
                    
                    print(f"Stock actualizado: {insumo.nombre} - Cantidad agregada: {cantidad} - Nuevo stock: {insumo.cantidad}")
                
            except Insumo.DoesNotExist:
                # Si llegamos aquí, la validación falló
                pass
        
        # Calcular total
        instance.calcular_total()
        
        return instance
