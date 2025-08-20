from rest_framework import serializers
from django.utils import timezone
from .models import VentaServicio, DetalleVentaServicio
from api.clientes.serializers import ClienteSerializer
from api.servicios.serializers import ServicioSerializer
from api.manicuristas.serializers import ManicuristaSerializer


class DetalleVentaServicioSerializer(serializers.ModelSerializer):
    servicio_info = ServicioSerializer(source='servicio', read_only=True)
    
    class Meta:
        model = DetalleVentaServicio
        fields = '__all__'

    def validate(self, data):
        """Validar que el subtotal sea correcto"""
        precio_unitario = data.get('precio_unitario')
        cantidad = data.get('cantidad')
        descuento_linea = data.get('descuento_linea', 0)
        
        if precio_unitario is None and data.get('servicio'):
            precio_unitario = data['servicio'].precio # Usar precio del servicio si no se proporciona
        
        if precio_unitario is not None and cantidad is not None:
            subtotal_calculado = (precio_unitario * cantidad) - descuento_linea
            if 'subtotal' in data and abs(data['subtotal'] - subtotal_calculado) > 0.01:
                raise serializers.ValidationError({
                    'subtotal': f'El subtotal debe ser {subtotal_calculado}'
                })
        
        return data


class VentaServicioSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información completa
    cliente_info = ClienteSerializer(source='cliente', read_only=True)
    manicurista_info = ManicuristaSerializer(source='manicurista', read_only=True)
    servicio_info = ServicioSerializer(source='servicio', read_only=True) # Para compatibilidad
    
    # CORREGIDO: Información de múltiples citas
    citas_info = serializers.SerializerMethodField()
    citas_ids = serializers.SerializerMethodField()
    
    # Detalles de la venta
    detalles = DetalleVentaServicioSerializer(many=True, read_only=True)
    
    # Campos calculados
    subtotal = serializers.ReadOnlyField()
    total_con_descuento = serializers.ReadOnlyField()
    puede_cancelar = serializers.ReadOnlyField()
    puede_marcar_pagada = serializers.ReadOnlyField()
    es_desde_cita = serializers.ReadOnlyField()
    
    # CORREGIDO: Campos para fechas formateadas
    fecha_para_mostrar = serializers.SerializerMethodField()
    hora_para_mostrar = serializers.SerializerMethodField()
    
    class Meta:
        model = VentaServicio
        fields = '__all__'

    def get_citas_info(self, obj):
        """Obtener información de todas las citas asociadas"""
        try:
            from api.citas.serializers import CitaSerializer
            citas = obj.citas.all()
            return CitaSerializer(citas, many=True).data
        except ImportError:
            return []

    def get_citas_ids(self, obj):
        """Obtener IDs de las citas asociadas"""
        return list(obj.citas.values_list('id', flat=True))

    def get_fecha_para_mostrar(self, obj):
        """Obtener fecha formateada"""
        return obj.get_fecha_para_mostrar()

    def get_hora_para_mostrar(self, obj):
        """Obtener hora formateada"""
        return obj.get_hora_para_mostrar()

    def validate_cliente(self, value):
        """Validar que el cliente esté activo"""
        if not value.estado:
            raise serializers.ValidationError("El cliente seleccionado no está activo")
        return value

    def validate_manicurista(self, value):
        """Validar que la manicurista esté activa"""
        if value.estado != 'activo':
            raise serializers.ValidationError("La manicurista seleccionada no está activa")
        return value

    def validate_servicio(self, value):
        """Validar que el servicio esté activo (para el campo principal 'servicio')"""
        if value and value.estado != 'activo':
            raise serializers.ValidationError("El servicio seleccionado no está activo")
        return value

    def validate_metodo_pago(self, value):
        """Validar que el método de pago sea válido"""
        metodos_validos = ['efectivo', 'transferencia']
        if value not in metodos_validos:
            raise serializers.ValidationError(
                f"Método de pago no válido. Opciones: {', '.join(metodos_validos)}"
            )
        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        # Estas validaciones son más relevantes para VentaServicioCreateSerializer
        # Aquí solo se asegura la consistencia si los campos están presentes
        return data


class VentaServicioCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para crear ventas con múltiples detalles de servicio"""
    
    # CORREGIDO: Usar ListField para IDs de citas
    citas = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Lista de IDs de citas asociadas"
    )
    
    # Detalles de la venta para creación/actualización
    detalles = DetalleVentaServicioSerializer(many=True)
    
    class Meta:
        model = VentaServicio
        fields = [
            'cliente', 'manicurista', 'fecha_venta', 'estado', 'metodo_pago',
            'observaciones', 'porcentaje_comision', 'citas', 'cita', 'detalles'
        ]
        # Excluir 'servicio', 'cantidad', 'precio_unitario', 'descuento', 'total'
        # ya que se manejan a través de 'detalles' o se calculan automáticamente.
        extra_kwargs = {
            'servicio': {'required': False, 'allow_null': True},
            'cantidad': {'required': False},
            'precio_unitario': {'required': False},
            'descuento': {'required': False},
            'total': {'read_only': True}, # Total se calcula
            'comision_manicurista': {'read_only': True}, # Comisión se calcula
            'fecha_pago': {'read_only': True}, # Fecha de pago se establece automáticamente
        }

    def validate_metodo_pago(self, value):
        """Validar que el método de pago sea válido"""
        if value:
            metodos_validos = ['efectivo', 'transferencia']
            if value not in metodos_validos:
                raise serializers.ValidationError(
                    f"Método de pago no válido. Opciones: {', '.join(metodos_validos)}"
                )
        return value

    def validate_citas(self, value):
        """Validar que las citas existan y estén finalizadas"""
        if not value:
            return value
        
        try:
            from api.citas.models import Cita
            
            # Verificar que todas las citas existan
            citas_existentes = Cita.objects.filter(id__in=value)
            if len(citas_existentes) != len(value):
                citas_no_encontradas = set(value) - set(citas_existentes.values_list('id', flat=True))
                raise serializers.ValidationError(
                    f"Las siguientes citas no existen: {list(citas_no_encontradas)}"
                )
            
            # Verificar que todas estén finalizadas
            citas_no_finalizadas = citas_existentes.exclude(estado='finalizada')
            if citas_no_finalizadas.exists():
                ids_no_finalizadas = list(citas_no_finalizadas.values_list('id', flat=True))
                raise serializers.ValidationError(
                    f"Las siguientes citas no están finalizadas: {ids_no_finalizadas}"
                )
            
            return value
            
        except ImportError:
            # Si no existe el módulo de citas, permitir cualquier valor
            return value

    def create(self, validated_data):
        """Crear venta con múltiples detalles de servicio y citas"""
        detalles_data = validated_data.pop('detalles')
        citas_ids = validated_data.pop('citas', [])
        
        # Crear la venta principal
        venta = VentaServicio.objects.create(**validated_data)
        
        # Crear los detalles de la venta
        for detalle_data in detalles_data:
            DetalleVentaServicio.objects.create(venta=venta, **detalle_data)
        
        # Asignar citas si se proporcionaron
        if citas_ids:
            try:
                from api.citas.models import Cita
                citas = Cita.objects.filter(id__in=citas_ids)
                venta.citas.set(citas)
                
                # Establecer cita principal si no se proporcionó
                if not venta.cita and citas.exists():
                    venta.cita = citas.first()
                    venta.save(update_fields=['cita'])
                
                # Sincronizar fecha con las citas
                venta.sincronizar_con_citas() # Corregido el nombre de la función
            except ImportError:
                pass
        
        # La señal post_save de DetalleVentaServicio se encargará de actualizar el total de la venta
        return venta

    def update(self, instance, validated_data):
        """Actualizar venta con múltiples detalles de servicio y citas"""
        detalles_data = validated_data.pop('detalles', None)
        citas_ids = validated_data.pop('citas', None)
        
        # Actualizar campos básicos de la venta
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar detalles de la venta
        if detalles_data is not None:
            # Eliminar detalles existentes que no estén en los nuevos datos
            detalle_ids_existentes = [d.id for d in instance.detalles.all()]
            detalle_ids_enviados = [d.get('id') for d in detalles_data if d.get('id')]

            # Eliminar detalles que ya no están en la lista enviada
            for detalle_id in set(detalle_ids_existentes) - set(detalle_ids_enviados):
                instance.detalles.filter(id=detalle_id).delete()

            # Crear o actualizar detalles
            for detalle_data in detalles_data:
                detalle_id = detalle_data.get('id')
                if detalle_id:
                    # Actualizar detalle existente
                    detalle_instance = instance.detalles.get(id=detalle_id)
                    for attr, value in detalle_data.items():
                        setattr(detalle_instance, attr, value)
                    detalle_instance.save()
                else:
                    # Crear nuevo detalle
                    DetalleVentaServicio.objects.create(venta=instance, **detalle_data)
        
        # Actualizar citas si se proporcionaron
        if citas_ids is not None:
            try:
                from api.citas.models import Cita
                citas = Cita.objects.filter(id__in=citas_ids)
                instance.citas.set(citas)
                
                # Establecer cita principal si no existe
                if not instance.cita and citas.exists():
                    instance.cita = citas.first()
                
                # Sincronizar fecha con las citas
                instance.sincronizar_con_citas()
            except ImportError:
                pass
        
        instance.save()
        return instance


class VentaServicioUpdateEstadoSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estado de la venta como en citas"""
    
    class Meta:
        model = VentaServicio
        fields = ['estado', 'metodo_pago', 'observaciones']

    def validate_estado(self, value):
        """Validar transiciones de estado válidas"""
        if self.instance:
            estado_actual = self.instance.estado
            
            # Definir transiciones válidas (igual que citas)
            transiciones_validas = {
                'pendiente': ['pagada', 'cancelada'],
                'pagada': [],  # No se puede cambiar desde pagada
                'cancelada': []  # No se puede cambiar desde cancelada
            }
            
            if value not in transiciones_validas.get(estado_actual, []):
                raise serializers.ValidationError(
                    f"No se puede cambiar de '{estado_actual}' a '{value}'"
                )
        
        return value

    def validate_metodo_pago(self, value):
        """Validar método de pago al marcar como pagada"""
        # Obtener el estado del contexto de validación
        request = self.context.get('request')
        estado = None
        
        if request and hasattr(request, 'data'):
            estado = request.data.get('estado')
        
        # Si se está marcando como pagada, el método de pago es obligatorio
        if estado == 'pagada' and not value:
            raise serializers.ValidationError(
                "Debe seleccionar un método de pago para marcar como pagada"
            )
        
        # Validar que sea uno de los métodos permitidos
        if value and value not in ['efectivo', 'transferencia']:
            raise serializers.ValidationError(
                "Método de pago no válido. Solo se permite efectivo o transferencia"
            )
        
        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        estado = data.get('estado')
        metodo_pago = data.get('metodo_pago')
        
        # Si se marca como pagada, debe tener método de pago
        if estado == 'pagada' and not metodo_pago:
            raise serializers.ValidationError({
                'metodo_pago': 'Debe seleccionar un método de pago para marcar como pagada'
            })
        
        return data

    def update(self, instance, validated_data):
        """Actualizar estado y manejar lógica especial"""
        nuevo_estado = validated_data.get('estado')
        
        # Si se marca como pagada, establecer fecha de pago
        if nuevo_estado == 'pagada' and not instance.fecha_pago:
            instance.fecha_pago = timezone.now()
        
        return super().update(instance, validated_data)
