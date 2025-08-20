from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction
from api.novedades.models import Novedad
from api.novedades.serializers import NovedadSerializer, NovedadDetailSerializer
from api.citas.models import Cita
from django.core.mail import send_mail
from django.conf import settings


class NovedadViewSet(viewsets.ModelViewSet):
    queryset = Novedad.objects.all().order_by('-fecha', '-created_at')

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return NovedadDetailSerializer
        return NovedadSerializer

    def get_queryset(self):
        queryset = Novedad.objects.select_related('manicurista').all()
        
        # Filtros opcionales
        manicurista_id = self.request.query_params.get('manicurista')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        estado = self.request.query_params.get('estado')

        if manicurista_id:
            queryset = queryset.filter(manicurista_id=manicurista_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset.order_by('-fecha', '-created_at')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Crear nueva novedad con validaciones mejoradas y conexión con citas"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            # Crear la novedad
            novedad = serializer.save()
            
            # Conectar con citas - cancelar citas afectadas
            self._manejar_citas_afectadas(novedad)
            
            # Retornar con serializer de detalle
            detail_serializer = NovedadDetailSerializer(novedad)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Actualizar novedad existente"""
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Actualizar la novedad
            novedad = serializer.save()
            
            # Reconectar con citas si es necesario
            self._manejar_citas_afectadas(novedad)

            # Retornar con serializer de detalle
            detail_serializer = NovedadDetailSerializer(novedad)
            return Response(detail_serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['patch'])
    def anular(self, request, pk=None):
        """Anular una novedad con motivo"""
        try:
            novedad = self.get_object()
            motivo_anulacion = request.data.get('motivo_anulacion')
            
            if not motivo_anulacion:
                return Response(
                    {'error': 'El motivo de anulación es requerido'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Anular la novedad
            novedad.estado = 'anulada'
            novedad.motivo_anulacion = motivo_anulacion
            novedad.fecha_anulacion = timezone.now()
            novedad.save()
            
            # Reactivar citas que fueron canceladas por esta novedad
            self._reactivar_citas_canceladas(novedad)
            
            detail_serializer = NovedadDetailSerializer(novedad)
            return Response({
                'message': 'Novedad anulada exitosamente',
                'data': detail_serializer.data
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def disponibilidad_citas(self, request):
        """Verificar disponibilidad de horarios para citas considerando novedades"""
        manicurista_id = request.query_params.get('manicurista')
        fecha = request.query_params.get('fecha')
        
        if not manicurista_id or not fecha:
            return Response(
                {'error': 'Se requiere manicurista y fecha'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Buscar novedades activas para esa manicurista en esa fecha
            novedades = Novedad.objects.filter(
                manicurista_id=manicurista_id,
                fecha=fecha,
                estado__in=['ausente', 'tardanza']  # Excluir anuladas
            )
            
            disponibilidad = {
                'fecha': fecha,
                'manicurista_id': manicurista_id,
                'horario_base': {
                    'entrada': '10:00',
                    'salida': '20:00'
                },
                'novedades': [],
                'horarios_no_disponibles': [],
                'mensaje': 'Horario normal disponible'
            }
            
            for novedad in novedades:
                novedad_info = {
                    'id': novedad.id,
                    'estado': novedad.estado,
                    'tipo_ausencia': novedad.tipo_ausencia,
                    'motivo': novedad.motivo
                }
                
                if novedad.estado == 'ausente':
                    if novedad.tipo_ausencia == 'completa':
                        disponibilidad['horarios_no_disponibles'] = ['10:00-20:00']
                        disponibilidad['mensaje'] = 'Manicurista ausente todo el día'
                        novedad_info['horarios_afectados'] = '10:00-20:00'
                    elif novedad.tipo_ausencia == 'por_horas':
                        horario_ausencia = f"{novedad.hora_inicio_ausencia.strftime('%H:%M')}-{novedad.hora_fin_ausencia.strftime('%H:%M')}"
                        disponibilidad['horarios_no_disponibles'].append(horario_ausencia)
                        novedad_info['horarios_afectados'] = horario_ausencia
                        
                elif novedad.estado == 'tardanza':
                    hora_llegada = novedad.hora_entrada.strftime('%H:%M')
                    horario_tardanza = f"10:00-{hora_llegada}"
                    disponibilidad['horarios_no_disponibles'].append(horario_tardanza)
                    disponibilidad['mensaje'] = f'Manicurista llega tarde a las {hora_llegada}'
                    novedad_info['horarios_afectados'] = horario_tardanza
                
                disponibilidad['novedades'].append(novedad_info)
            
            return Response(disponibilidad)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def novedades_hoy(self, request):
        """Obtener novedades del día actual"""
        hoy = timezone.localdate()
        novedades = self.get_queryset().filter(fecha=hoy)
        serializer = NovedadDetailSerializer(novedades, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de novedades"""
        queryset = self.get_queryset()
        
        stats = {
            'total': queryset.count(),
            'ausentes': queryset.filter(estado='ausente').count(),
            'tardanzas': queryset.filter(estado='tardanza').count(),
            'anuladas': queryset.filter(estado='anulada').count(),
            'hoy': queryset.filter(fecha=timezone.localdate()).count(),
        }
        
        return Response(stats)

    def _manejar_citas_afectadas(self, novedad):
        """Manejar citas afectadas por la novedad"""
        try:
            # Buscar citas activas para esa manicurista en esa fecha
            citas_afectadas = Cita.objects.filter(
                manicurista=novedad.manicurista,
                fecha_cita=novedad.fecha,
                estado__in=['pendiente', 'confirmada', 'en_proceso']
            )

            for cita in citas_afectadas:
                # Verificar si la cita está en el horario afectado
                if self._cita_en_horario_afectado(cita, novedad):
                    # Cancelar la cita
                    cita.estado = 'cancelada_por_novedad'
                    cita.motivo_cancelacion = f"Novedad de manicurista: {novedad.get_estado_display()}"
                    cita.novedad_relacionada = novedad
                    cita.save()

                    # Enviar notificación al cliente
                    self._notificar_cliente_cancelacion(cita, novedad)
                    
        except Exception as e:
            print(f"Error manejando citas afectadas: {e}")

    def _cita_en_horario_afectado(self, cita, novedad):
        """Verificar si una cita está en el horario afectado por la novedad"""
        if novedad.estado == 'ausente':
            if novedad.tipo_ausencia == 'completa':
                return True  # Toda la jornada afectada
            elif novedad.tipo_ausencia == 'por_horas':
                # Verificar si la hora de la cita está en el rango de ausencia
                hora_cita = cita.hora_cita
                return (novedad.hora_inicio_ausencia <= hora_cita <= novedad.hora_fin_ausencia)
        
        elif novedad.estado == 'tardanza':
            # Verificar si la cita es antes de la hora de llegada
            hora_cita = cita.hora_cita
            return hora_cita < novedad.hora_entrada
        
        return False

    def _reactivar_citas_canceladas(self, novedad):
        """Reactivar citas que fueron canceladas por esta novedad"""
        try:
            citas_canceladas = Cita.objects.filter(
                novedad_relacionada=novedad,
                estado='cancelada_por_novedad'
            )
            
            for cita in citas_canceladas:
                cita.estado = 'pendiente'
                cita.motivo_cancelacion = None
                cita.novedad_relacionada = None
                cita.save()
                
                # Notificar al cliente que su cita fue reactivada
                self._notificar_cliente_reactivacion(cita)
                
        except Exception as e:
            print(f"Error reactivando citas: {e}")

    def _notificar_cliente_cancelacion(self, cita, novedad):
        """Notificar al cliente sobre la cancelación de su cita"""
        try:
            if hasattr(cita, 'cliente') and cita.cliente.email:
                send_mail(
                    subject='Cancelación de tu cita en Spa',
                    message=f"Hola {cita.cliente.nombre},\n\n"
                            f"Lamentamos informarte que tu cita con {novedad.manicurista.nombres} "
                            f"el {novedad.fecha.strftime('%d/%m/%Y')} a las {cita.hora_cita.strftime('%H:%M')} "
                            f"ha sido cancelada debido a una novedad de la manicurista.\n\n"
                            f"Motivo: {novedad.get_estado_display()}\n\n"
                            f"Te invitamos a agendar una nueva cita desde nuestra plataforma.\n\n"
                            f"Gracias por tu comprensión.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[cita.cliente.email],
                    fail_silently=True
                )
        except Exception as e:
            print(f"Error enviando notificación de cancelación: {e}")

    def _notificar_cliente_reactivacion(self, cita):
        """Notificar al cliente que su cita fue reactivada"""
        try:
            if hasattr(cita, 'cliente') and cita.cliente.email:
                send_mail(
                    subject='Tu cita ha sido reactivada',
                    message=f"Hola {cita.cliente.nombre},\n\n"
                            f"Te informamos que tu cita con {cita.manicurista.nombres} "
                            f"el {cita.fecha_cita.strftime('%d/%m/%Y')} a las {cita.hora_cita.strftime('%H:%M')} "
                            f"ha sido reactivada.\n\n"
                            f"La novedad que causó la cancelación ha sido anulada.\n\n"
                            f"Tu cita está confirmada nuevamente.\n\n"
                            f"¡Te esperamos!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[cita.cliente.email],
                    fail_silently=True
                )
        except Exception as e:
            print(f"Error enviando notificación de reactivación: {e}")
