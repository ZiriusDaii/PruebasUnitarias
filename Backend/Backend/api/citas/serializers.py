from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, time
from .models import Cita
from api.clientes.models import Cliente
from api.servicios.models import Servicio
from api.manicuristas.models import Manicurista
from api.clientes.serializers import ClienteSerializer
from api.servicios.serializers import ServicioSerializer
from api.manicuristas.serializers import ManicuristaSerializer


class CitaSerializer(serializers.ModelSerializer):
    # Campos de solo lectura para mostrar información completa
    cliente_info = ClienteSerializer(source='cliente', read_only=True)
    manicurista_info = ManicuristaSerializer(source='manicurista', read_only=True)
    servicio_info = ServicioSerializer(source='servicio', read_only=True)
    
    # NUEVO: Información de todos los servicios
    servicios_info = ServicioSerializer(source='servicios', many=True, read_only=True)
    
    # Campos calculados
    duracion_formateada = serializers.ReadOnlyField()
    puede_finalizar = serializers.ReadOnlyField()
    puede_cancelar = serializers.ReadOnlyField()
    
    # NUEVO: Campos para múltiples servicios
    servicios = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.filter(estado='activo'),
        many=True,
        required=False
    )
    
    class Meta:
        model = Cita
        fields = '__all__'

    def validate_fecha_cita(self, value):
        """Validar que la fecha no sea en el pasado"""
        if value < timezone.now().date():
            raise serializers.ValidationError("La fecha de la cita no puede ser en el pasado")
        return value

    def validate_hora_cita(self, value):
        """Validar horario de trabajo"""
        # --- CAMBIO AQUÍ: Horario de 10:00 AM a 8:00 PM ---
        if value < time(10, 0) or value >= time(20, 0):
            raise serializers.ValidationError("La hora debe estar entre 10:00 AM y 8:00 PM")
        return value

    def validate_cliente(self, value):
        """Validar que el cliente esté activo"""
        if not value.estado:
            raise serializers.ValidationError("El cliente seleccionado no está activo")
        return value

    def validate_manicurista(self, value):
        """Validar que la manicurista esté activa y disponible"""
        if value.estado != 'activo':
            raise serializers.ValidationError("La manicurista seleccionada no está activa")
        if not value.disponible:
            raise serializers.ValidationError("La manicurista seleccionada no está disponible")
        return value

    def validate_servicio(self, value):
        """Validar que el servicio esté activo"""
        if value and value.estado != 'activo':
            raise serializers.ValidationError("El servicio seleccionado no está activo")
        return value

    def validate_servicios(self, value):
        """Validar que todos los servicios estén activos"""
        if not value:
            raise serializers.ValidationError("Debe seleccionar al menos un servicio")
        
        for servicio in value:
            if servicio.estado != 'activo':
                raise serializers.ValidationError(f"El servicio '{servicio.nombre}' no está activo")
        
        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        fecha_cita = data.get('fecha_cita')
        hora_cita = data.get('hora_cita')
        manicurista = data.get('manicurista')

        # Verificar disponibilidad de la manicurista en esa fecha y hora
        if fecha_cita and hora_cita and manicurista:
            # Excluir la cita actual si estamos editando
            queryset = Cita.objects.filter(
                manicurista=manicurista,
                fecha_cita=fecha_cita,
                hora_cita=hora_cita,
                estado__in=['pendiente', 'en_proceso']
            )
            
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            
            if queryset.exists():
                raise serializers.ValidationError({
                    'hora_cita': 'La manicurista ya tiene una cita programada en esta fecha y hora'
                })

        return data


class CitaCreateSerializer(serializers.ModelSerializer):
    """Serializer específico para crear citas con múltiples servicios"""
    
    servicios = serializers.PrimaryKeyRelatedField(
        queryset=Servicio.objects.filter(estado='activo'),
        many=True,
        required=True
    )
    
    class Meta:
        model = Cita
        fields = [
            'cliente', 'manicurista', 'servicio', 'servicios',
            'fecha_cita', 'hora_cita', 'observaciones'
        ]

    def validate_servicios(self, value):
        """Validar que se seleccionen servicios"""
        if not value:
            raise serializers.ValidationError("Debe seleccionar al menos un servicio")
        return value

    def create(self, validated_data):
        """Crear cita con múltiples servicios"""
        servicios_data = validated_data.pop('servicios', [])
        
        # Si no hay servicio principal, usar el primero de la lista
        if not validated_data.get('servicio') and servicios_data:
            validated_data['servicio'] = servicios_data[0]
        
        # Calcular totales
        precio_total = sum(servicio.precio for servicio in servicios_data)
        duracion_total = sum(servicio.duracion for servicio in servicios_data)
        
        validated_data['precio_total'] = precio_total
        validated_data['duracion_total'] = duracion_total
        
        # Mantener compatibilidad
        if validated_data.get('servicio'):
            validated_data['precio_servicio'] = validated_data['servicio'].precio
            validated_data['duracion_estimada'] = validated_data['servicio'].duracion
        
        # Crear la cita
        cita = super().create(validated_data)
        
        # Asignar servicios
        cita.servicios.set(servicios_data)
        
        return cita

    def update(self, instance, validated_data):
        """Actualizar cita con múltiples servicios"""
        servicios_data = validated_data.pop('servicios', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar servicios si se proporcionaron
        if servicios_data is not None:
            instance.servicios.set(servicios_data)
            
            # Recalcular totales
            precio_total = sum(servicio.precio for servicio in servicios_data)
            duracion_total = sum(servicio.duracion for servicio in servicios_data)
            
            instance.precio_total = precio_total
            instance.duracion_total = duracion_total
            
            # Actualizar servicio principal si no está definido
            if not instance.servicio and servicios_data:
                instance.servicio = servicios_data[0]
                instance.precio_servicio = servicios_data[0].precio
                instance.duracion_estimada = servicios_data[0].duracion
        
        instance.save()
        return instance


class CitaUpdateEstadoSerializer(serializers.ModelSerializer):
    """Serializer para actualizar solo el estado de la cita"""
    
    class Meta:
        model = Cita
        fields = ['estado', 'observaciones']

    def validate_estado(self, value):
        """Validar transiciones de estado válidas"""
        if self.instance:
            estado_actual = self.instance.estado
            
            # Definir transiciones válidas
            transiciones_validas = {
                'pendiente': ['en_proceso', 'cancelada'],
                'en_proceso': ['finalizada', 'cancelada'],
                'finalizada': [],  # No se puede cambiar desde finalizada
                'cancelada': []    # No se puede cambiar desde cancelada
            }
            
            if value not in transiciones_validas.get(estado_actual, []):
                raise serializers.ValidationError(
                    f"No se puede cambiar de '{estado_actual}' a '{value}'"
                )
        
        return value

    def update(self, instance, validated_data):
        """Actualizar estado y manejar lógica especial"""
        nuevo_estado = validated_data.get('estado')
        
        # Si se finaliza la cita, establecer fecha de finalización
        if nuevo_estado == 'finalizada' and not instance.fecha_finalizacion:
            instance.fecha_finalizacion = timezone.now()
        
        return super().update(instance, validated_data)


class BuscarClienteSerializer(serializers.Serializer):
    """Serializer para búsqueda de clientes"""
    query = serializers.CharField(
        max_length=100,
        help_text="Nombre o documento del cliente"
    )

    def validate_query(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "La búsqueda debe tener al menos 2 caracteres"
            )
        return value.strip()
