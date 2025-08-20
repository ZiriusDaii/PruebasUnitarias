from rest_framework import serializers
from api.novedades.models import Novedad
from api.manicuristas.serializers import ManicuristaSerializer
from datetime import time, date, timedelta
from django.utils import timezone
from datetime import datetime, time
from django.utils.timezone import localdate


class NovedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Novedad
        fields = '__all__'

    def validate_fecha(self, value):
        # Forzar que siempre sea una fecha local, sin hora
        if isinstance(value, datetime):
            value = localdate(value)

        today = localdate()
        tomorrow = today + timedelta(days=1)
        estado = self.initial_data.get('estado')

        if not value:
            raise serializers.ValidationError("Debe seleccionar una fecha.")

        if estado == 'ausente' and value < tomorrow:
            raise serializers.ValidationError(
                "Para ausencias, debe seleccionar una fecha a partir de mañana."
            )
        elif estado == 'tardanza' and value < today:
            raise serializers.ValidationError(
                "Para tardanzas, debe seleccionar una fecha a partir de hoy."
            )
        elif value < today:
            raise serializers.ValidationError(
                "No se puede registrar una novedad en fecha anterior a hoy."
            )

        return value

    def validate_manicurista(self, value):
        if not value:
            raise serializers.ValidationError("Debe seleccionar una manicurista.")
        return value

    def validate_estado(self, value):
        if not value:
            raise serializers.ValidationError("Debe seleccionar un estado.")
        return value

    def validate_hora_entrada(self, value):
        if value and not (Novedad.HORA_MIN_PERMITIDA <= value <= Novedad.HORA_MAX_PERMITIDA):
            raise serializers.ValidationError(
                f"La hora de entrada debe estar entre {Novedad.HORA_MIN_PERMITIDA.strftime('%H:%M')} "
                f"y {Novedad.HORA_MAX_PERMITIDA.strftime('%H:%M')}."
            )
        return value

    def validate_hora_inicio_ausencia(self, value):
        if value and not (Novedad.HORA_MIN_PERMITIDA <= value <= Novedad.HORA_MAX_PERMITIDA):
            raise serializers.ValidationError(
                f"La hora de inicio debe estar entre {Novedad.HORA_MIN_PERMITIDA.strftime('%H:%M')} "
                f"y {Novedad.HORA_MAX_PERMITIDA.strftime('%H:%M')}."
            )
        return value

    def validate_hora_fin_ausencia(self, value):
        if value and not (Novedad.HORA_MIN_PERMITIDA <= value <= Novedad.HORA_MAX_PERMITIDA):
            raise serializers.ValidationError(
                f"La hora de fin debe estar entre {Novedad.HORA_MIN_PERMITIDA.strftime('%H:%M')} "
                f"y {Novedad.HORA_MAX_PERMITIDA.strftime('%H:%M')}."
            )
        return value

    def validate(self, data):
        # Solo validar duplicados si no es una actualización
        if not self.instance:
            if Novedad.objects.filter(
                manicurista=data.get('manicurista'),
                fecha=data.get('fecha')
            ).exclude(estado='anulada').exists():
                raise serializers.ValidationError(
                    "Ya existe una novedad activa para esta manicurista en la fecha indicada."
                )

        estado = data.get('estado')
        tipo_ausencia = data.get('tipo_ausencia')
        fecha = data.get('fecha')

        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)

        if fecha and estado:
            if estado == 'ausente' and fecha < tomorrow:
                raise serializers.ValidationError({
                    'fecha': 'Para ausencias, debe seleccionar una fecha a partir de mañana.'
                })
            elif estado == 'tardanza' and fecha < today:
                raise serializers.ValidationError({
                    'fecha': 'Para tardanzas, debe seleccionar una fecha a partir de hoy.'
                })

        if estado == 'tardanza':
            hora_entrada = data.get('hora_entrada')
            if not hora_entrada:
                raise serializers.ValidationError("Debe ingresar la hora de entrada para una tardanza.")
            if hora_entrada <= Novedad.HORA_ENTRADA_BASE:
                raise serializers.ValidationError(
                    f"Para registrar tardanza, la hora debe ser posterior a {Novedad.HORA_ENTRADA_BASE.strftime('%H:%M')}."
                )
            data['hora_salida'] = Novedad.HORA_SALIDA_BASE
            data['tipo_ausencia'] = None
            data['hora_inicio_ausencia'] = None
            data['hora_fin_ausencia'] = None

        elif estado == 'ausente':
            if not tipo_ausencia:
                raise serializers.ValidationError("Debe indicar el tipo de ausencia.")

            if tipo_ausencia == 'completa':
                data['hora_entrada'] = None
                data['hora_salida'] = None
                data['hora_inicio_ausencia'] = Novedad.HORA_ENTRADA_BASE
                data['hora_fin_ausencia'] = Novedad.HORA_SALIDA_BASE

            elif tipo_ausencia == 'por_horas':
                hora_inicio = data.get('hora_inicio_ausencia')
                hora_fin = data.get('hora_fin_ausencia')
                if not hora_inicio:
                    raise serializers.ValidationError("Debe ingresar la hora de inicio de ausencia.")
                if not hora_fin:
                    data['hora_fin_ausencia'] = Novedad.HORA_SALIDA_BASE
                    hora_fin = data['hora_fin_ausencia']
                if hora_inicio >= hora_fin:
                    raise serializers.ValidationError(
                        "La hora de inicio de ausencia debe ser anterior a la de fin."
                    )
                data['hora_entrada'] = Novedad.HORA_ENTRADA_BASE
                data['hora_salida'] = Novedad.HORA_SALIDA_BASE

        return data


class NovedadDetailSerializer(serializers.ModelSerializer):
    manicurista = ManicuristaSerializer(read_only=True)
    mensaje_personalizado = serializers.SerializerMethodField()
    horario_base = serializers.SerializerMethodField()
    validacion_fecha = serializers.SerializerMethodField()
    citas_afectadas = serializers.SerializerMethodField()

    class Meta:
        model = Novedad
        fields = '__all__'

    def get_horario_base(self, obj):
        return {
            'entrada': Novedad.HORA_ENTRADA_BASE.strftime('%H:%M'),
            'salida': Novedad.HORA_SALIDA_BASE.strftime('%H:%M')
        }

    def get_validacion_fecha(self, obj):
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        return {
            'hoy': today.isoformat(),
            'manana': tomorrow.isoformat(),
            'reglas': {
                'ausente': 'Debe programarse con al menos un día de anticipación (desde mañ ana)',
                'tardanza': 'Puede registrarse desde hoy'
            }
        }

    def get_mensaje_personalizado(self, obj):
        nombre = obj.manicurista.nombres
        if obj.estado == 'tardanza':
            if obj.hora_entrada:
                return f"La manicurista {nombre} llegó tarde a las {obj.hora_entrada.strftime('%I:%M %p')}."
            else:
                return f"La manicurista {nombre} llegó tarde, sin hora registrada."
        elif obj.estado == 'ausente':
            if obj.tipo_ausencia == 'completa':
                return f"La manicurista {nombre} se ausentó todo el día (10:00 AM - 8:00 PM)."
            elif obj.tipo_ausencia == 'por_horas':
                if obj.hora_inicio_ausencia and obj.hora_fin_ausencia:
                    return (f"La manicurista {nombre} se ausentó desde "
                            f"{obj.hora_inicio_ausencia.strftime('%I:%M %p')} hasta "
                            f"{obj.hora_fin_ausencia.strftime('%I:%M %p')}.")
                else:
                    return f"La manicurista {nombre} se ausenta por horas, sin horario definido."
        elif obj.estado == 'anulada':
            return f"Novedad de {nombre} anulada: {obj.motivo_anulacion}"
        return f"La manicurista {nombre} tiene una novedad registrada."

    def get_citas_afectadas(self, obj):
        """Obtener información de citas afectadas por esta novedad"""
        try:
            from api.citas.models import Cita
            citas = Cita.objects.filter(
                novedad_relacionada=obj
            ).values('id', 'hora_cita', 'estado', 'cliente__nombre')
            return list(citas)
        except:
            return []
