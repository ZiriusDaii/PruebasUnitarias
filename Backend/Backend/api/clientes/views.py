from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from .models import Cliente
from .serializers import (
    ClienteSerializer, 
    RegistroClienteSerializer,
    CambiarContraseñaSerializer,
    LoginClienteSerializer
)

Usuario = get_user_model()

class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Cliente.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado según la acción.
        Para crear un cliente, usamos RegistroClienteSerializer que también crea un usuario.
        """
        if self.action == 'create':
            return RegistroClienteSerializer
        elif self.action == 'login':
            return LoginClienteSerializer
        elif self.action == 'cambiar_password':
            return CambiarContraseñaSerializer
        return self.serializer_class
    
    def create(self, request, *args, **kwargs):
        """
        Sobrescribimos el método create para manejar la creación de cliente y usuario.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # El RegistroClienteSerializer se encarga de crear tanto el usuario como el cliente
            result = serializer.save()
            cliente = result['cliente']
            
            # Enviar correo si se generó contraseña temporal
            if hasattr(cliente, 'contraseña_generada'):
                try:
                    self.enviar_correo_bienvenida(cliente, cliente.contraseña_generada)
                except Exception as e:
                    # Log del error pero no fallar la creación
                    print(f"Error enviando correo: {e}")
            
            # Devolvemos solo los datos del cliente en la respuesta
            cliente_serializer = ClienteSerializer(cliente)
            response_data = cliente_serializer.data
            
            # Agregar mensaje personalizado
            if hasattr(cliente, 'contraseña_generada'):
                response_data['mensaje'] = f"Cliente registrado exitosamente. Se envió un correo a {cliente.correo_electronico} con la contraseña temporal y el enlace para cambiarla."
            else:
                response_data['mensaje'] = "Cliente registrado exitosamente."
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Manejar errores específicos
            error_message = str(e)
            if "already exists" in error_message.lower():
                return Response(
                    {"error": "Ya existe un cliente o usuario con estos datos"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"error": f"Error al crear el cliente: {error_message}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def enviar_correo_bienvenida(self, cliente, contraseña_temporal):
        """
        Envía correo de bienvenida con contraseña temporal y enlace de login
        """
        asunto = 'Bienvenido al sistema - Contraseña temporal'
        
        # URL del login principal - MODIFICA ESTA URL SEGÚN TU APLICACIÓN
        login_url = f"http://localhost:5173/login?email={cliente.correo_electronico}&type=cliente"
        
        # Crear el mensaje HTML
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3b82f6;">¡Bienvenido al sistema, {cliente.nombre}!</h2>
                <p>Tu cuenta ha sido creada exitosamente. Aquí están tus datos de acceso:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                    <h3 style="margin-top: 0; color: #3b82f6;">Datos de acceso:</h3>
                    <p><strong>Número de documento:</strong> {cliente.documento}</p>
                    <p><strong>Contraseña temporal:</strong> <span style="color: #dc3545; font-weight: bold; font-size: 18px;">{contraseña_temporal}</span></p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                    <h3 style="margin-top: 0; color: #1976d2;">🔗 Enlace de acceso:</h3>
                    <p>Para iniciar sesión, haz clic en el siguiente enlace:</p>
                    <p style="text-align: center; margin: 15px 0;">
                        <a href="{login_url}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                            🔑 Iniciar Sesión
                        </a>
                    </p>
                    <p style="font-size: 12px; color: #666;">
                        Si el botón no funciona, copia y pega este enlace en tu navegador:<br>
                        <a href="{login_url}" style="color: #3b82f6;">{login_url}</a>
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
                        <li><strong>Serás redirigido al login</strong> para ingresar con tu nueva contraseña</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #e8f5e8; border-radius: 8px;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold;">¡Gracias y bienvenido! 🎉</p>
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
        ¡Bienvenido al sistema, {cliente.nombre}!
        
        Tu cuenta ha sido creada exitosamente.
        
        DATOS DE ACCESO:
        - Número de documento: {cliente.documento}
        - Contraseña temporal: {contraseña_temporal}
        
        ENLACE DE ACCESO:
        {login_url}
        
        IMPORTANTE: Esta contraseña temporal debe ser cambiada en tu primer inicio de sesión por seguridad.
        
        ¡Gracias y bienvenido!
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [cliente.correo_electronico],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login para clientes
        """
        serializer = LoginClienteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        documento = serializer.validated_data['documento']
        contraseña = serializer.validated_data['contraseña']
        
        try:
            cliente = Cliente.objects.get(documento=documento)
            
            if not cliente.verificar_contraseña_temporal(contraseña):
                return Response(
                    {'error': 'Credenciales incorrectas'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            if not cliente.estado:
                return Response(
                    {'error': 'Cuenta inactiva. Contacta al administrador'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            response_data = {
                'mensaje': 'Login exitoso',
                'cliente': ClienteSerializer(cliente).data,
                'debe_cambiar_contraseña': cliente.debe_cambiar_contraseña
            }
            
            return Response(response_data)
            
        except Cliente.DoesNotExist:
            return Response(
                {'error': 'Credenciales incorrectas'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=True, methods=['post'])
    def cambiar_password(self, request, pk=None):
        """
        Cambiar contraseña temporal por una nueva
        """
        cliente = self.get_object()
        serializer = CambiarContraseñaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        contraseña_temporal = serializer.validated_data['contraseña_temporal']
        nueva_contraseña = serializer.validated_data['nueva_contraseña']
        
        if not cliente.verificar_contraseña_temporal(contraseña_temporal):
            return Response(
                {'error': 'Contraseña temporal incorrecta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar contraseña
        cliente.cambiar_contraseña(nueva_contraseña)
        
        # Recargar desde la base de datos para verificar
        cliente.refresh_from_db()
        
        # Enviar correo de confirmación
        try:
            self.enviar_correo_confirmacion_cambio(cliente)
        except Exception as e:
            print(f"Error enviando correo de confirmación: {e}")
        
        return Response({
            'mensaje': 'Contraseña cambiada exitosamente. Se ha enviado una confirmación a tu correo.',
            'debe_cambiar_contraseña': cliente.debe_cambiar_contraseña
        })
    
    def enviar_correo_confirmacion_cambio(self, cliente):
        """
        Envía correo de confirmación cuando se actualiza la contraseña
        """
        asunto = 'Contraseña actualizada exitosamente'
        
        # URL del login principal
        login_url = f"http://localhost:5173/login?email={cliente.correo_electronico}&type=cliente"
        
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">✅ Contraseña actualizada exitosamente</h2>
                <p>Hola <strong>{cliente.nombre}</strong>,</p>
                <p>Te confirmamos que tu contraseña ha sido actualizada correctamente en nuestro sistema.</p>
                
                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">🔐 Cambio de contraseña completado</h3>
                    <p style="margin-bottom: 0;"><strong>Fecha y hora:</strong> {cliente.updated_at.strftime('%d/%m/%Y a las %H:%M')}</p>
                    <p style="margin-bottom: 0;"><strong>Usuario:</strong> {cliente.nombre}</p>
                    <p style="margin-bottom: 0;"><strong>Documento:</strong> {cliente.documento}</p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2196f3;">
                    <h3 style="margin-top: 0; color: #1976d2;">🔗 Acceder al sistema</h3>
                    <p>Ya puedes iniciar sesión con tu nueva contraseña:</p>
                    <p style="text-align: center; margin: 15px 0;">
                        <a href="{login_url}" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                            🚀 Iniciar Sesión
                        </a>
                    </p>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
                    <p style="margin: 0; color: #495057; font-weight: bold;">¡Tu cuenta está segura! 🛡️</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mensaje_texto = f"""
        Contraseña actualizada exitosamente
        
        Hola {cliente.nombre},
        
        Te confirmamos que tu contraseña ha sido actualizada correctamente.
        
        Ya puedes iniciar sesión con tu nueva contraseña en:
        {login_url}
        
        ¡Tu cuenta está segura!
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [cliente.correo_electronico],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @action(detail=True, methods=['post'])
    def resetear_password(self, request, pk=None):
        """
        Resetear contraseña (solo admin) - genera nueva contraseña temporal
        """
        cliente = self.get_object()
        nueva_contraseña_temporal = cliente.generar_contraseña_temporal()
        cliente.save()
        
        # Enviar correo con nueva contraseña
        try:
            self.enviar_correo_reset_contraseña(cliente, nueva_contraseña_temporal)
        except Exception as e:
            print(f"Error enviando correo: {e}")
        
        return Response({
            'mensaje': f'Contraseña reseteada. Se envió un correo a {cliente.correo_electronico} con la nueva contraseña temporal y el enlace para cambiarla.'
        })
    
    def enviar_correo_reset_contraseña(self, cliente, nueva_contraseña):
        """
        Envía correo con nueva contraseña temporal después del reset
        """
        asunto = 'Contraseña reseteada - Nueva contraseña temporal'
        
        # URL del login principal
        login_url = f"http://localhost:5173/login?email={cliente.correo_electronico}&type=cliente"
        
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #dc3545;">🔄 Contraseña reseteada</h2>
                <p>Hola <strong>{cliente.nombre}</strong>,</p>
                <p>Tu contraseña ha sido reseteada por el administrador del sistema.</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                    <h3 style="margin-top: 0; color: #dc3545;">🔑 Nueva contraseña temporal:</h3>
                    <p style="font-size: 24px; font-weight: bold; color: #dc3545; text-align: center; background-color: white; padding: 15px; border-radius: 6px; margin: 15px 0;">
                        {nueva_contraseña}
                    </p>
                    <p style="margin-bottom: 0; text-align: center; color: #666; font-size: 14px;">
                        <strong>Número de documento:</strong> {cliente.documento}
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
                </div>
                
                <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                    <h3 style="margin-top: 0; color: #856404;">⚠️ IMPORTANTE:</h3>
                    <p><strong>Debes cambiar esta contraseña temporal inmediatamente por seguridad.</strong></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        mensaje_texto = f"""
        Contraseña reseteada
        
        Hola {cliente.nombre},
        
        Tu contraseña ha sido reseteada por el administrador del sistema.
        
        NUEVA CONTRASEÑA TEMPORAL: {nueva_contraseña}
        NÚMERO DE DOCUMENTO: {cliente.documento}
        
        ENLACE DE ACCESO:
        {login_url}
        
        IMPORTANTE: Debes cambiar esta contraseña temporal inmediatamente por seguridad.
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [cliente.correo_electronico],
            html_message=mensaje_html,
            fail_silently=False,
        )
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        Sobrescribimos el método destroy para eliminar tanto el cliente como el usuario asociado.
        """
        cliente = self.get_object()
        
        try:
            # Buscar el usuario asociado por documento y correo
            usuario_asociado = None
            
            # Intentar encontrar el usuario por documento
            try:
                usuario_asociado = Usuario.objects.get(
                    documento=cliente.documento,
                    correo_electronico=cliente.correo_electronico
                )
            except Usuario.DoesNotExist:
                # Si no se encuentra por documento, intentar solo por correo
                try:
                    usuario_asociado = Usuario.objects.get(
                        correo_electronico=cliente.correo_electronico
                    )
                except Usuario.DoesNotExist:
                    pass
            
            # Eliminar el cliente primero
            cliente_nombre = cliente.nombre
            cliente.delete()
            
            # Si encontramos un usuario asociado, eliminarlo también
            if usuario_asociado:
                # Verificar que el usuario tenga rol de cliente antes de eliminarlo
                if hasattr(usuario_asociado, 'rol') and usuario_asociado.rol:
                    if usuario_asociado.rol.nombre.lower() == 'cliente':
                        usuario_asociado.delete()
                        mensaje = f"Cliente '{cliente_nombre}' y usuario asociado eliminados exitosamente"
                    else:
                        mensaje = f"Cliente '{cliente_nombre}' eliminado. Usuario asociado mantenido (no es rol cliente)"
                else:
                    usuario_asociado.delete()
                    mensaje = f"Cliente '{cliente_nombre}' y usuario asociado eliminados exitosamente"
            else:
                mensaje = f"Cliente '{cliente_nombre}' eliminado exitosamente (no se encontró usuario asociado)"
            
            return Response(
                {"message": mensaje}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            # Si algo falla, la transacción se revierte automáticamente
            return Response(
                {"error": f"Error al eliminar el cliente: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def by_documento(self, request):
        """
        Endpoint para buscar cliente por número de documento.
        """
        documento = request.query_params.get('documento')
        if not documento:
            return Response(
                {"error": "Se requiere el parámetro documento"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cliente = self.get_queryset().get(documento=documento)
            serializer = self.get_serializer(cliente)
            return Response(serializer.data)
        except Cliente.DoesNotExist:
            return Response(
                {"error": "No se encontró el cliente con ese documento"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Endpoint para buscar clientes por nombre o documento.
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {"error": "Se requiere el parámetro q"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        clientes = self.get_queryset().filter(
            nombre__icontains=query
        ) | self.get_queryset().filter(
            documento__icontains=query
        )
        
        serializer = self.get_serializer(clientes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """
        Endpoint para listar solo los clientes activos.
        """
        clientes = self.get_queryset().filter(estado=True)
        serializer = self.get_serializer(clientes, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def activar(self, request, pk=None):
        """
        Endpoint para activar un cliente.
        """
        cliente = self.get_object()
        cliente.estado = True
        cliente.save()
        serializer = self.get_serializer(cliente)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def desactivar(self, request, pk=None):
        """
        Endpoint para desactivar un cliente.
        """
        cliente = self.get_object()
        cliente.estado = False
        cliente.save()
        serializer = self.get_serializer(cliente)
        return Response(serializer.data)
