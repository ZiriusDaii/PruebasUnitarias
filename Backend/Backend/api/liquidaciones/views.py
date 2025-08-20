from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Q
from datetime import datetime
from decimal import Decimal
from .models import Liquidacion
from .serializers import (
    LiquidacionSerializer, 
    LiquidacionDetailSerializer, 
    LiquidacionCreateSerializer,
    LiquidacionUpdateSerializer
)
from api.citas.models import Cita
from api.manicuristas.models import Manicurista


class LiquidacionViewSet(viewsets.ModelViewSet):
    queryset = Liquidacion.objects.all()
    serializer_class = LiquidacionSerializer

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return LiquidacionDetailSerializer
        elif self.action == 'create':
            return LiquidacionCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return LiquidacionUpdateSerializer
        return LiquidacionSerializer

    def get_queryset(self):
        queryset = Liquidacion.objects.select_related('manicurista').all()
        manicurista_id = self.request.query_params.get('manicurista')
        estado = self.request.query_params.get('estado')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_final = self.request.query_params.get('fecha_final')

        if manicurista_id:
            queryset = queryset.filter(manicurista_id=manicurista_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio and fecha_final:
            queryset = queryset.filter(fecha_inicio=fecha_inicio, fecha_final=fecha_final)

        return queryset.order_by('-fecha_inicio')

    @action(detail=False, methods=['post'])
    def calcular_citas_completadas(self, request):
        """
        Calcular el total de citas completadas para una manicurista en un período
        """
        manicurista_id = request.data.get('manicurista_id')
        fecha_inicio = request.data.get('fecha_inicio')
        fecha_final = request.data.get('fecha_final')

        if not all([manicurista_id, fecha_inicio, fecha_final]):
            return Response({
                "error": "Se requieren manicurista_id, fecha_inicio y fecha_final"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            manicurista = Manicurista.objects.get(id=manicurista_id)
        except Manicurista.DoesNotExist:
            return Response({"error": "Manicurista no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Convertir fechas string a objetos date
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_final_obj = datetime.strptime(fecha_final, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener citas completadas en el período
        citas_completadas = Cita.objects.filter(
            manicurista=manicurista,
            fecha_cita__range=(fecha_inicio_obj, fecha_final_obj),
            estado='finalizada'
        ).select_related('cliente', 'servicio').prefetch_related('servicios')

        # Calcular totales usando precio_total (que incluye todos los servicios)
        total_citas = citas_completadas.aggregate(
            total=Sum('precio_total')
        )['total'] or Decimal('0.00')

        # Calcular comisión del 50% y redondear a 2 decimales
        comision_50_porciento = (total_citas * Decimal('0.5')).quantize(Decimal('0.01'))
        cantidad_citas = citas_completadas.count()

        # Obtener detalles de las citas
        citas_detalle = []
        for cita in citas_completadas:
            # Obtener todos los servicios de la cita
            servicios_nombres = [servicio.nombre for servicio in cita.servicios.all()]
            if not servicios_nombres and cita.servicio:
                servicios_nombres = [cita.servicio.nombre]
        
            citas_detalle.append({
                'id': cita.id,
                'fecha': cita.fecha_cita,
                'hora': cita.hora_cita.strftime('%H:%M'),
                'cliente': cita.cliente.nombre,
                'servicios': servicios_nombres,
                'precio_total': float(cita.precio_total),
                'fecha_finalizacion': cita.fecha_finalizacion.strftime('%Y-%m-%d %H:%M:%S') if cita.fecha_finalizacion else None
            })

        return Response({
            'manicurista': {
                'id': manicurista.id,
                'nombre': manicurista.nombre,
                'email': getattr(manicurista, 'correo', '')
            },
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_final': fecha_final
            },
            'resumen_citas': {
                'total_citas_completadas': float(total_citas),
                'comision_50_porciento': float(comision_50_porciento),
                'cantidad_citas': cantidad_citas,
                'promedio_por_cita': float(total_citas / cantidad_citas) if cantidad_citas > 0 else 0
            },
            'citas_detalle': citas_detalle,
            'valor_sugerido_liquidacion': float(comision_50_porciento)
        })

    @action(detail=False, methods=['post'])
    def crear_liquidacion_automatica(self, request):
        """
        Crear liquidación automáticamente basada en citas completadas
        """
        manicurista_id = request.data.get('manicurista_id')
        fecha_inicio = request.data.get('fecha_inicio')
        fecha_final = request.data.get('fecha_final')
        bonificacion = request.data.get('bonificacion', 0)

        if not all([manicurista_id, fecha_inicio, fecha_final]):
            return Response({
                "error": "Se requieren manicurista_id, fecha_inicio y fecha_final"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            manicurista = Manicurista.objects.get(id=manicurista_id)
        except Manicurista.DoesNotExist:
            return Response({"error": "Manicurista no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        try:
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_final_obj = datetime.strptime(fecha_final, '%Y-%m-%d').date()
        except ValueError:
            return Response({"error": "Formato de fecha inválido. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar si ya existe una liquidación para este período
        if Liquidacion.objects.filter(
            manicurista=manicurista,
            fecha_inicio=fecha_inicio_obj,
            fecha_final=fecha_final_obj
        ).exists():
            return Response({
                "error": "Ya existe una liquidación para esta manicurista en este período"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calcular valor basado en citas completadas
        total_citas = Cita.objects.filter(
            manicurista=manicurista,
            fecha_cita__range=(fecha_inicio_obj, fecha_final_obj),
            estado='finalizada'
        ).aggregate(total=Sum('precio_total'))['total'] or Decimal('0.00')

        # Calcular el 50% de comisión y redondear a 2 decimales
        comision_50_porciento = (total_citas * Decimal('0.5')).quantize(Decimal('0.01'))

        # Crear la liquidación
        liquidacion = Liquidacion.objects.create(
            manicurista=manicurista,
            fecha_inicio=fecha_inicio_obj,
            fecha_final=fecha_final_obj,
            valor=comision_50_porciento,
            bonificacion=Decimal(str(bonificacion)).quantize(Decimal('0.01')),
            observaciones=f"Liquidación automática basada en {Cita.objects.filter(manicurista=manicurista, fecha_cita__range=(fecha_inicio_obj, fecha_final_obj), estado='finalizada').count()} citas completadas"
        )

        serializer = LiquidacionDetailSerializer(liquidacion)
        return Response({
            'mensaje': 'Liquidación creada exitosamente',
            'liquidacion': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def recalcular_citas_completadas(self, request, pk=None):
        """
        Recalcula las citas completadas para una liquidación específica
        """
        liquidacion = self.get_object()
        valor_anterior = liquidacion.citascompletadas
        nuevo_valor = liquidacion.recalcular_citas_completadas()
        
        return Response({
            'mensaje': 'Citas completadas recalculadas exitosamente',
            'valor_anterior': float(valor_anterior),
            'nuevo_valor': float(nuevo_valor),
            'diferencia': float(nuevo_valor - valor_anterior),
            'liquidacion': LiquidacionDetailSerializer(liquidacion).data
        })

    @action(detail=False, methods=['get'])
    def por_manicurista(self, request):
        manicurista_id = request.query_params.get('id')
        if manicurista_id:
            liquidaciones = Liquidacion.objects.filter(manicurista_id=manicurista_id)
            serializer = LiquidacionDetailSerializer(liquidaciones, many=True)
            return Response(serializer.data)
        return Response({"error": "Se requiere el ID del manicurista"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        liquidaciones = Liquidacion.objects.filter(estado='pendiente')
        serializer = LiquidacionDetailSerializer(liquidaciones, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def marcar_como_pagada(self, request, pk=None):
        liquidacion = self.get_object()
        if liquidacion.estado == 'pagado':
            return Response({"error": "Esta liquidación ya ha sido pagada"}, status=status.HTTP_400_BAD_REQUEST)
        liquidacion.estado = 'pagado'
        liquidacion.save()
        serializer = LiquidacionDetailSerializer(liquidacion)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def detalle_citas(self, request, pk=None):
        """
        Obtiene el detalle de todas las citas completadas en el período de la liquidación
        """
        liquidacion = self.get_object()
        
        citas_completadas = Cita.objects.filter(
            manicurista=liquidacion.manicurista,
            fecha_cita__range=(liquidacion.fecha_inicio, liquidacion.fecha_final),
            estado='finalizada'
        ).select_related('cliente', 'servicio').prefetch_related('servicios')

        citas_detalle = []
        for cita in citas_completadas:
            # Obtener todos los servicios de la cita
            servicios_info = []
            for servicio in cita.servicios.all():
                servicios_info.append({
                    'id': servicio.id,
                    'nombre': servicio.nombre,
                    'precio': float(servicio.precio)
                })
            
            # Si no hay servicios en la relación many-to-many, usar el servicio principal
            if not servicios_info and cita.servicio:
                servicios_info.append({
                    'id': cita.servicio.id,
                    'nombre': cita.servicio.nombre,
                    'precio': float(cita.servicio.precio)
                })
            
            citas_detalle.append({
                'id': cita.id,
                'fecha': cita.fecha_cita,
                'hora': cita.hora_cita,
                'cliente': {
                    'id': cita.cliente.id,
                    'nombre': cita.cliente.nombre,
                    'documento': getattr(cita.cliente, 'documento', '')
                },
                'servicios': servicios_info,
                'precio_total': float(cita.precio_total),
                'fecha_finalizacion': cita.fecha_finalizacion
            })

        return Response({
            'liquidacion': {
                'id': liquidacion.id,
                'manicurista': liquidacion.manicurista.nombre,
                'periodo': f"{liquidacion.fecha_inicio} - {liquidacion.fecha_final}",
                'total_citas_completadas': float(liquidacion.total_servicios_completados),
                'comision_50_porciento': float(liquidacion.citascompletadas),
                'cantidad_citas': liquidacion.cantidad_servicios_completados,
                'total_a_pagar': float(liquidacion.total_a_pagar)
            },
            'citas_detalle': citas_detalle
        })

    @action(detail=False, methods=['get'])
    def estadisticas_generales(self, request):
        """
        Obtiene estadísticas generales de liquidaciones
        """
        from django.utils import timezone
        from datetime import timedelta

        # Fecha actual y rangos
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        inicio_año = hoy.replace(month=1, day=1)

        # Estadísticas básicas
        total_liquidaciones = Liquidacion.objects.count()
        liquidaciones_pendientes = Liquidacion.objects.filter(estado='pendiente').count()
        liquidaciones_pagadas = Liquidacion.objects.filter(estado='pagado').count()

        # Totales del mes
        liquidaciones_mes = Liquidacion.objects.filter(
            fecha_inicio__gte=inicio_mes
        )
        total_a_pagar_mes = liquidaciones_mes.aggregate(
            total=Sum('valor')
        )['total'] or Decimal('0.00')

        # Manicuristas con más liquidaciones
        manicuristas_top = Liquidacion.objects.values(
            'manicurista__nombre'
        ).annotate(
            total_liquidaciones=Sum('valor'),
            cantidad=Count('id')
        ).order_by('-total_liquidaciones')[:5]

        return Response({
            'resumen': {
                'total_liquidaciones': total_liquidaciones,
                'liquidaciones_pendientes': liquidaciones_pendientes,
                'liquidaciones_pagadas': liquidaciones_pagadas,
                'total_a_pagar_mes': float(total_a_pagar_mes)
            },
            'manicuristas_top': list(manicuristas_top),
            'periodo_consultado': {
                'inicio_mes': inicio_mes,
                'fecha_actual': hoy
            }
        })
