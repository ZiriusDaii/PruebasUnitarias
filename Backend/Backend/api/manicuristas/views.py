from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Count, Sum
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Manicurista
from .serializers import (
    ManicuristaSerializer, 
    CambiarContraseñaSerializer,
    LoginManicuristaSerializer
)

Usuario = get_user_model()


class ManicuristaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar operaciones CRUD en Manicuristas.
    """
    queryset = Manicurista.objects.all()
    serializer_class = ManicuristaSerializer
    
    def get_queryset(self):
        """
        Opcionalmente filtra por estado o disponibilidad.
        """
        queryset = Manicurista.objects.all()
        estado = self.request.query_params.get('estado', None)
        disponible = self.request.query_params.get('disponible', None)
        
        if estado is not None:
            queryset = queryset.filter(estado=estado)
        
        if disponible is not None:
            disponible_bool = disponible.lower() == 'true'
            queryset = queryset.filter(disponible=disponible_bool)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Crear una nueva manicurista y enviar correo con contraseña temporal.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        manicurista = serializer.save()
        
        # Enviar correo con la contraseña temporal
        try:
            self.enviar_correo_bienvenida(manicurista, manicurista.contraseña_generada)
        except Exception as e:
            # Log del error pero no fallar la creación
            print(f"Error enviando correo: {e}")
        
        # Preparar respuesta sin mostrar la contraseña encriptada
        response_data = ManicuristaSerializer(manicurista).data
        response_data['mensaje'] = f"Manicurista registrada exitosamente. Se envió un correo a {manicurista.correo} con la contraseña temporal y el enlace para cambiarla."
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Sobrescribimos el método destroy para eliminar tanto la manicurista como el usuario asociado.
        """
        manicurista = self.get_object()
        
        try:
            # Buscar el usuario asociado por documento y correo
            usuario_asociado = None
            
            # Intentar encontrar el usuario por documento
            try:
                usuario_asociado = Usuario.objects.get(
                    documento=manicurista.numero_documento,
                    correo_electronico=manicurista.correo
                )
            except Usuario.DoesNotExist:
                # Si no se encuentra por documento, intentar solo por correo
                try:
                    usuario_asociado = Usuario.objects.get(
                        correo_electronico=manicurista.correo
                    )
                except Usuario.DoesNotExist:
                    pass
            
            # Eliminar la manicurista primero
            manicurista_nombre = manicurista.nombre
            manicurista.delete()
            
            # Si encontramos un usuario asociado, eliminarlo también
            if usuario_asociado:
                # Verificar que el usuario tenga rol de manicurista antes de eliminarlo
                if hasattr(usuario_asociado, 'rol') and usuario_asociado.rol:
                    if usuario_asociado.rol.nombre.lower() == 'manicurista':
                        usuario_asociado.delete()
                        mensaje = f"Manicurista '{manicurista_nombre}' y usuario asociado eliminados exitosamente"
                    else:
                        mensaje = f"Manicurista '{manicurista_nombre}' eliminada. Usuario asociado mantenido (no es rol manicurista)"
                else:
                    usuario_asociado.delete()
                    mensaje = f"Manicurista '{manicurista_nombre}' y usuario asociado eliminados exitosamente"
            else:
                mensaje = f"Manicurista '{manicurista_nombre}' eliminada exitosamente (no se encontró usuario asociado)"
            
            return Response(
                {"message": mensaje}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            # Si algo falla, la transacción se revierte automáticamente
            return Response(
                {"error": f"Error al eliminar la manicurista: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def enviar_correo_bienvenida(self, manicurista, contraseña_temporal):
        """
        Envía correo de bienvenida con contraseña temporal y enlace de login
        """
        asunto = 'Bienvenida al sistema - Contraseña temporal'
        
        # URL del login principal - MODIFICA ESTA URL SEGÚN TU APLICACIÓN
        login_url = f"http://localhost:5173/login?email={manicurista.correo}&type=manicurista"
        
        # Crear el mensaje HTML
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #ec4899;">¡Bienvenida al sistema, {manicurista.nombre}!</h2>
                <p>Tu cuenta ha sido creada exitosamente. Aquí están tus datos de acceso:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ec4899;">
                    <h3 style="margin-top: 0; color: #ec4899;">Datos de acceso:</h3>
                    <p><strong>Número de documento:</strong> {manicurista.numero_documento}</p>
                    <p><strong>Contraseña temporal:</strong> <span style="color: #dc3545; font-weight: bold; font-size: 18px;">{contraseña_temporal}</span></p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                    <h3 style="margin-top: 0; color: #1976d2;">🔗 Enlace de acceso:</h3>
                    <p>Para iniciar sesión, haz clic en el siguiente enlace:</p>
                    <p style="text-align: center; margin: 15px 0;">
                        <a href="{login_url}" style="background-color: #ec4899; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                            🔑 Iniciar Sesión
                        </a>
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                        <a href="{login_url}" style="color: #ec4899;">{login_url}</a>
                    </p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">⚠️ IMPORTANTE - Proceso de cambio de contraseña:</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li><strong>Inicia sesión</strong> con tu número de documento y la contraseña temporal</li>
                        <li><strong>El sistema detectará automáticamente</strong> que tienes una contraseña temporal</li>
                        <li><strong>Te aparecerá un formulario</strong> con los siguientes campos:
                            <ul style="margin: 8px 0; padding-left: 20px;">
                                <li>Contraseña temporal (la que te enviamos)</li>
                                <li>Nueva contraseña (mínimo 8 caracteres)</li>
                                <li>Confirmar nueva contraseña</li>
                            </ul>
                        </li>
                        <li><strong>Después del cambio exitoso</strong>, recibirás un correo de confirmación</li>
                        <li><strong>Serás redirigida al login</strong> para ingresar con tu nueva contraseña</li>
                    </ol>
                </div>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">📋 Resumen de pasos:</h3>
                    <p><strong>1.</strong> Haz clic en el enlace de arriba</p>
                    <p><strong>2.</strong> Tu correo estará pre-llenado: <strong>{manicurista.correo}</strong></p>
                    <p><strong>3.</strong> Ingresa la contraseña temporal: <strong>{contraseña_temporal}</strong></p>
                    <p><strong>4.</strong> Cambia tu contraseña por una segura</p>
                    <p><strong>5.</strong> ¡Listo! Ya puedes usar el sistema</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #e8f5e8; border-radius: 8px;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold;">¡Gracias y bienvenida al equipo! 🎉</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                        Si tienes alguna pregunta, contacta al administrador.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Mensaje de texto plano (fallback)
        mensaje_texto = f"""
        ¡Bienvenida al sistema, {manicurista.nombre}!
        
        Tu cuenta ha sido creada exitosamente.
        
        DATOS DE ACCESO:
        - Número de documento: {manicurista.numero_documento}
        - Contraseña temporal: {contraseña_temporal}
        
        ENLACE DE ACCESO:
        {login_url}
        
        PROCESO DE CAMBIO DE CONTRASEÑA:
        1. Haz clic en el enlace de arriba o cópialo en tu navegador
        2. Inicia sesión con tu documento y contraseña temporal
        3. El sistema te pedirá cambiar tu contraseña automáticamente
        4. Completa el formulario con:
           - Contraseña temporal (la que te enviamos)
           - Nueva contraseña (mínimo 8 caracteres)
           - Confirmar nueva contraseña
        5. Después del cambio, recibirás un correo de confirmación
        6. Serás redirigida al login para usar tu nueva contraseña
        
        IMPORTANTE: Esta contraseña temporal debe ser cambiada en tu primer inicio de sesión por seguridad.
        
        ¡Gracias y bienvenida al equipo!
        
        Si tienes alguna pregunta, contacta al administrador.
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [manicurista.correo],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login para manicuristas
        """
        serializer = LoginManicuristaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        numero_documento = serializer.validated_data['numero_documento']
        contraseña = serializer.validated_data['contraseña']
        
        try:
            manicurista = Manicurista.objects.get(numero_documento=numero_documento)
            
            if not manicurista.verificar_contraseña_temporal(contraseña):
                return Response(
                    {'error': 'Credenciales incorrectas'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if manicurista.estado != 'activo':
                return Response(
                    {'error': 'Cuenta inactiva. Contacta al administrador'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            response_data = {
                'mensaje': 'Login exitoso',
                'manicurista': ManicuristaSerializer(manicurista).data,
                'debe_cambiar_contraseña': manicurista.debe_cambiar_contraseña
            }
            
            return Response(response_data)
            
        except Manicurista.DoesNotExist:
            return Response(
                {'error': 'Credenciales incorrectas'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=True, methods=['post'])
    def cambiar_password(self, request, pk=None):
        """
        Cambiar contraseña temporal por una nueva
        """
        manicurista = self.get_object()
        serializer = CambiarContraseñaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        contraseña_temporal = serializer.validated_data['contraseña_temporal']
        nueva_contraseña = serializer.validated_data['nueva_contraseña']
        
        if not manicurista.verificar_contraseña_temporal(contraseña_temporal):
            return Response(
                {'error': 'Contraseña temporal incorrecta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar contraseña y verificar que se guarde
        print(f"Antes del cambio - debe_cambiar_contraseña: {manicurista.debe_cambiar_contraseña}")
        manicurista.cambiar_contraseña(nueva_contraseña)
        print(f"Después del cambio - debe_cambiar_contraseña: {manicurista.debe_cambiar_contraseña}")
        
        # Recargar desde la base de datos para verificar
        manicurista.refresh_from_db()
        print(f"Después de refresh_from_db - debe_cambiar_contraseña: {manicurista.debe_cambiar_contraseña}")
        
        # Enviar correo de confirmación
        try:
            self.enviar_correo_confirmacion_cambio(manicurista)
        except Exception as e:
            print(f"Error enviando correo de confirmación: {e}")
        
        return Response({
            'mensaje': 'Contraseña cambiada exitosamente. Se ha enviado una confirmación a tu correo.',
            'debe_cambiar_contraseña': manicurista.debe_cambiar_contraseña
        })
    
    def enviar_correo_confirmacion_cambio(self, manicurista):
        """
        Envía correo de confirmación cuando se actualiza la contraseña
        """
        asunto = 'Contraseña actualizada exitosamente'
        
        # URL del login principal
        login_url = f"http://localhost:5173/login?email={manicurista.correo}&type=manicurista"
        
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">✅ Contraseña actualizada exitosamente</h2>
                <p>Hola <strong>{manicurista.nombre}</strong>,</p>
                <p>Te confirmamos que tu contraseña ha sido actualizada correctamente en nuestro sistema.</p>
                
                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">🔐 Cambio de contraseña completado</h3>
                    <p style="margin-bottom: 0;"><strong>Fecha y hora:</strong> {manicurista.updated_at.strftime('%d/%m/%Y a las %H:%M')}</p>
                    <p style="margin-bottom: 0;"><strong>Usuario:</strong> {manicurista.nombre}</p>
                    <p style="margin-bottom: 0;"><strong>Documento:</strong> {manicurista.numero_documento}</p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                    <h3 style="margin-top: 0; color: #1976d2;">🔗 Acceder al sistema</h3>
                    <p>Ya puedes iniciar sesión con tu nueva contraseña:</p>
                    <p style="text-align: center; margin: 15px 0;">
                        <a href="{login_url}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                            🚀 Iniciar Sesión
                        </a>
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Enlace directo: <a href="{login_url}" style="color: #28a745;">{login_url}</a>
                    </p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">🔒 Seguridad</h3>
                    <p><strong>Si no realizaste este cambio:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Contacta inmediatamente al administrador del sistema</li>
                        <li>Tu cuenta podría estar comprometida</li>
                        <li>Se tomarán las medidas de seguridad necesarias</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0; color: #495057; font-weight: bold;">¡Tu cuenta está segura! 🛡️</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                        Gracias por mantener tu información actualizada.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mensaje_texto = f"""
        Contraseña actualizada exitosamente
        
        Hola {manicurista.nombre},
        
        Te confirmamos que tu contraseña ha sido actualizada correctamente en nuestro sistema.
        
        DETALLES DEL CAMBIO:
        - Fecha y hora: {manicurista.updated_at.strftime('%d/%m/%Y a las %H:%M')}
        - Usuario: {manicurista.nombre}
        - Documento: {manicurista.numero_documento}
        
        ACCEDER AL SISTEMA:
        Ya puedes iniciar sesión con tu nueva contraseña en:
        {login_url}
        
        SEGURIDAD:
        Si no realizaste este cambio, contacta inmediatamente al administrador del sistema.
        
        ¡Tu cuenta está segura!
        Gracias por mantener tu información actualizada.
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [manicurista.correo],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @action(detail=True, methods=['post'])
    def resetear_password(self, request, pk=None):
        """
        Resetear contraseña (solo admin) - genera nueva contraseña temporal
        """
        manicurista = self.get_object()
        nueva_contraseña_temporal = manicurista.generar_contraseña_temporal()
        manicurista.save()
        
        # Enviar correo con nueva contraseña
        try:
            self.enviar_correo_reset_contraseña(manicurista, nueva_contraseña_temporal)
        except Exception as e:
            print(f"Error enviando correo: {e}")
        
        return Response({
            'mensaje': f'Contraseña reseteada. Se envió un correo a {manicurista.correo} con la nueva contraseña temporal y el enlace para cambiarla.'
        })
    
    def enviar_correo_reset_contraseña(self, manicurista, nueva_contraseña):
        """
        Envía correo con nueva contraseña temporal después del reset
        """
        asunto = 'Contraseña reseteada - Nueva contraseña temporal'
        
        # URL del login principal
        login_url = f"http://localhost:5173/login?email={manicurista.correo}&type=manicurista"
        
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc3545;">🔄 Contraseña reseteada</h2>
                <p>Hola <strong>{manicurista.nombre}</strong>,</p>
                <p>Tu contraseña ha sido reseteada por el administrador del sistema.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="margin-top: 0; color: #dc3545;">🔑 Nueva contraseña temporal:</h3>
                    <p style="font-size: 24px; font-weight: bold; color: #dc3545; text-align: center; background-color: white; padding: 15px; border-radius: 6px; margin: 15px 0;">
                        {nueva_contraseña}
                    </p>
                    <p style="margin-bottom: 0; text-align: center; color: #666; font-size: 14px;">
                        <strong>Número de documento:</strong> {manicurista.numero_documento}
                    </p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                    <h3 style="margin-top: 0; color: #1976d2;">🔗 Enlace de acceso:</h3>
                    <p>Para iniciar sesión y cambiar tu contraseña, haz clic aquí:</p>
                    <p style="text-align: center; margin: 15px 0;">
                        <a href="{login_url}" style="background-color: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                            🔑 Cambiar Contraseña
                        </a>
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Si el botón no funciona, copia y pega este enlace:<br>
                        <a href="{login_url}" style="color: #dc3545;">{login_url}</a>
                    </p>
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">⚠️ IMPORTANTE:</h3>
                    <p><strong>Debes cambiar esta contraseña temporal inmediatamente por seguridad.</strong></p>
                    <p>El proceso es automático:</p>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Inicia sesión con la contraseña temporal</li>
                        <li>El sistema te pedirá cambiarla automáticamente</li>
                        <li>Ingresa una nueva contraseña segura</li>
                        <li>Recibirás confirmación por correo</li>
                    </ol>
                </div>
                
                <div style="background-color: #f8d7da; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="margin-top: 0; color: #721c24;">🚨 Seguridad</h3>
                    <p><strong>Si no solicitaste este cambio:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        <li>Contacta al administrador inmediatamente</li>
                        <li>Cambia tu contraseña lo antes posible</li>
                        <li>Revisa la actividad de tu cuenta</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0; color: #495057; font-weight: bold;">¿Necesitas ayuda? 🤝</p>
                    <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                        Contacta al administrador si tienes problemas.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mensaje_texto = f"""
        Contraseña reseteada
        
        Hola {manicurista.nombre},
        
        Tu contraseña ha sido reseteada por el administrador del sistema.
        
        NUEVA CONTRASEÑA TEMPORAL: {nueva_contraseña}
        NÚMERO DE DOCUMENTO: {manicurista.numero_documento}
        
        ENLACE DE ACCESO:
        {login_url}
        
        IMPORTANTE: 
        - Debes cambiar esta contraseña temporal inmediatamente por seguridad
        - El sistema te pedirá cambiarla automáticamente al iniciar sesión
        - Recibirás confirmación por correo después del cambio
        
        SEGURIDAD:
        Si no solicitaste este cambio, contacta al administrador inmediatamente.
        
        ¿Necesitas ayuda? Contacta al administrador.
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [manicurista.correo],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """
        Devuelve solo los manicuristas activos.
        """
        manicuristas = Manicurista.objects.filter(estado='activo')
        serializer = self.get_serializer(manicuristas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def disponibles(self, request):
        """
        Devuelve solo los manicuristas disponibles.
        """
        manicuristas = Manicurista.objects.filter(disponible=True, estado='activo')
        serializer = self.get_serializer(manicuristas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado del manicurista (activo/inactivo).
        """
        manicurista = self.get_object()
        nuevo_estado = 'inactivo' if manicurista.estado == 'activo' else 'activo'
        manicurista.estado = nuevo_estado
        manicurista.save()
        
        serializer = self.get_serializer(manicurista)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def cambiar_disponibilidad(self, request, pk=None):
        """
        Cambia la disponibilidad del manicurista.
        """
        manicurista = self.get_object()
        manicurista.disponible = not manicurista.disponible
        manicurista.save()
        
        serializer = self.get_serializer(manicurista)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Devuelve estadísticas de servicios realizados por el manicurista.
        """
        manicurista = self.get_object()
        
        # Esta implementación dependerá de cómo están relacionados los modelos
        try:
            from ventaservicios.models import VentaServicio
            
            # Total de servicios realizados
            total_servicios = VentaServicio.objects.filter(manicurista=manicurista).count()
            
            # Total facturado
            total_facturado = VentaServicio.objects.filter(manicurista=manicurista).aggregate(
                total=Sum('total')
            )['total'] or 0
            
            return Response({
                'total_servicios': total_servicios,
                'total_facturado': total_facturado,
            })
        except ImportError:
            return Response({
                'mensaje': 'Estadísticas no disponibles',
                'total_servicios': 0,
                'total_facturado': 0,
            })
