from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import Usuario
from .serializers import (
    UsuarioSerializer, 
    UsuarioDetailSerializer,
    CambiarContraseñaUsuarioSerializer,
    LoginUsuarioSerializer
)


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Usuario.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = Usuario.objects.all().order_by('-created_at')
    # permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """
        Retorna el serializer adecuado según la acción que se esté realizando.
        """
        if self.action == 'retrieve' or self.action == 'list_detail':
            return UsuarioDetailSerializer
        return UsuarioSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Crear un nuevo usuario y enviar correo con contraseña temporal si no se proporciona contraseña.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        
        # Si se generó una contraseña temporal, enviar correo
        if hasattr(usuario, 'contraseña_generada'):
            try:
                self.enviar_correo_bienvenida(usuario, usuario.contraseña_generada)
            except Exception as e:
                # Log del error pero no fallar la creación
                print(f"Error enviando correo: {e}")
        
        # Preparar respuesta
        response_data = UsuarioSerializer(usuario).data
        if hasattr(usuario, 'contraseña_generada'):
            response_data['mensaje'] = f"Usuario registrado exitosamente. Se envió un correo a {usuario.correo_electronico} con la contraseña temporal y el enlace para cambiarla."
        else:
            response_data['mensaje'] = "Usuario registrado exitosamente."
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, *args, **kwargs):
        """
        Elimina un usuario y sus registros relacionados en las tablas de clientes y manicuristas.
        """
        try:
            usuario = self.get_object()
            
            # Verificar si es administrador
            if usuario.rol and usuario.rol.nombre.lower() == 'administrador':
                return Response(
                    {"error": "No se puede eliminar un usuario administrador"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Usar transacción para asegurar consistencia
            with transaction.atomic():
                # Obtener el nombre del rol para determinar qué registros relacionados eliminar
                rol_nombre = usuario.rol.nombre.lower() if usuario.rol else None
                
                # Eliminar registros relacionados según el rol
                if rol_nombre == 'cliente':
                    # Importar aquí para evitar importaciones circulares
                    from api.clientes.models import Cliente
                    try:
                        # Buscar cliente por documento y correo ya que no hay relación directa con usuario
                        cliente = Cliente.objects.filter(
                            documento=usuario.documento,
                            correo_electronico=usuario.correo_electronico
                        ).first()
                        
                        if cliente:
                            cliente_id = cliente.id
                            cliente.delete()
                            print(f"Cliente relacionado eliminado: {cliente_id}")
                        else:
                            print(f"No se encontró cliente con documento {usuario.documento} y correo {usuario.correo_electronico}")
                    except Exception as e:
                        print(f"Error al eliminar cliente relacionado: {str(e)}")
                
                elif rol_nombre == 'manicurista':
                    # Importar aquí para evitar importaciones circulares
                    from api.manicuristas.models import Manicurista
                    try:
                        manicurista = Manicurista.objects.get(usuario=usuario)
                        manicurista.delete()
                        print(f"Manicurista relacionada eliminada: {manicurista.id}")
                    except Manicurista.DoesNotExist:
                        print(f"No se encontró manicurista relacionada para usuario {usuario.id}")
                
                # Eliminar el usuario
                usuario_id = usuario.id
                usuario_nombre = usuario.nombre
                usuario.delete()
                
                return Response(
                    {
                        "mensaje": f"Usuario '{usuario_nombre}' y sus registros relacionados eliminados exitosamente",
                        "usuario_id": usuario_id
                    }, 
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            print(f"Error al eliminar usuario: {str(e)}")
            return Response(
                {"error": f"Error al eliminar usuario: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def enviar_correo_bienvenida(self, usuario, contraseña_temporal):
        """
        Envía correo de bienvenida con contraseña temporal y enlace de login
        """
        asunto = 'Bienvenido al sistema - Contraseña temporal'
        
        # URL del login principal - MODIFICA ESTA URL SEGÚN TU APLICACIÓN
        login_url = f"http://localhost:5173/login?email={usuario.correo_electronico}&type=usuario"
        
        # Crear el mensaje HTML
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #3b82f6;">¡Bienvenido al sistema, {usuario.nombre}!</h2>
                <p>Tu cuenta ha sido creada exitosamente. Aquí están tus datos de acceso:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #3b82f6;">
                    <h3 style="margin-top: 0; color: #3b82f6;">Datos de acceso:</h3>
                    <p><strong>Correo electrónico:</strong> {usuario.correo_electronico}</p>
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
                        <li><strong>Inicia sesión</strong> con tu correo electrónico y la contraseña temporal</li>
                        <li><strong>El sistema detectará automáticamente</strong> que tienes una contraseña temporal</li>
                        <li><strong>Te aparecerá un formulario</strong> con los siguientes campos:
                            <ul style="margin: 8px 0; padding-left: 20px;">
                                <li>Contraseña temporal (la que te enviamos)</li>
                                <li>Nueva contraseña (mínimo 6 caracteres)</li>
                                <li>Confirmar nueva contraseña</li>
                            </ul>
                        </li>
                        <li><strong>Después del cambio exitoso</strong>, recibirás un correo de confirmación</li>
                        <li><strong>Serás redirigido al login</strong> para ingresar con tu nueva contraseña</li>
                    </ol>
                </div>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #e8f5e8; border-radius: 8px;">
                    <p style="margin: 0; color: #2e7d32; font-weight: bold;">¡Gracias y bienvenido al equipo! 🎉</p>
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
        ¡Bienvenido al sistema, {usuario.nombre}!
        
        Tu cuenta ha sido creada exitosamente.
        
        DATOS DE ACCESO:
        - Correo electrónico: {usuario.correo_electronico}
        - Contraseña temporal: {contraseña_temporal}
        
        ENLACE DE ACCESO:
        {login_url}
        
        IMPORTANTE: Esta contraseña temporal debe ser cambiada en tu primer inicio de sesión por seguridad.
        
        ¡Gracias y bienvenido al equipo!
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.correo_electronico],
            html_message=mensaje_html,
            fail_silently=False,
        )

    # --- Acciones Personalizadas ---
    @action(detail=False, methods=['get'], url_path='detallado')
    def list_detail(self, request):
        usuarios = self.get_queryset()
        serializer = UsuarioDetailSerializer(usuarios, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        usuarios = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(usuarios, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='por-rol')
    def by_rol(self, request):
        rol_id = request.query_params.get('rol_id')
        if not rol_id:
            return Response(
                {"error": "Se requiere el parámetro rol_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            rol_id = int(rol_id)
            usuarios = self.get_queryset().filter(rol_id=rol_id)
            serializer = self.get_serializer(usuarios, many=True, context={'request': request})
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "El parámetro rol_id debe ser un número entero."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # ENDPOINTS para contraseña temporal
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login para usuarios con verificación de contraseña temporal
        """
        serializer = LoginUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        correo_electronico = serializer.validated_data['correo_electronico']
        contraseña = serializer.validated_data['contraseña']
        
        try:
            usuario = Usuario.objects.get(correo_electronico=correo_electronico)
            
            # Verificar si debe usar contraseña temporal o contraseña normal
            if usuario.debe_cambiar_contraseña and usuario.contraseña_temporal:
                # Verificar contraseña temporal
                if not usuario.verificar_contraseña_temporal(contraseña):
                    return Response(
                        {'error': 'Credenciales incorrectas'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            else:
                # Verificar contraseña normal
                if not usuario.check_password(contraseña):
                    return Response(
                        {'error': 'Credenciales incorrectas'}, 
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            if not usuario.is_active:
                return Response(
                    {'error': 'Cuenta inactiva. Contacta al administrador'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            response_data = {
                'mensaje': 'Login exitoso',
                'usuario': UsuarioDetailSerializer(usuario).data,
                'debe_cambiar_contraseña': usuario.debe_cambiar_contraseña
            }
            
            return Response(response_data)
            
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Credenciales incorrectas'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    @action(detail=True, methods=['post'], url_path='cambiar-contraseña')
    def cambiar_contraseña(self, request, pk=None):
        """
        Cambiar contraseña temporal por una nueva
        """
        usuario = self.get_object()
        serializer = CambiarContraseñaUsuarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        contraseña_temporal = serializer.validated_data['contraseña_temporal']
        nueva_contraseña = serializer.validated_data['nueva_contraseña']
        
        if not usuario.verificar_contraseña_temporal(contraseña_temporal):
            return Response(
                {'error': 'Contraseña temporal incorrecta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar contraseña
        usuario.cambiar_contraseña(nueva_contraseña)
        
        # Enviar correo de confirmación
        try:
            self.enviar_correo_confirmacion_cambio(usuario)
        except Exception as e:
            print(f"Error enviando correo de confirmación: {e}")
        
        return Response({
            'mensaje': 'Contraseña cambiada exitosamente. Se ha enviado una confirmación a tu correo.',
            'debe_cambiar_contraseña': usuario.debe_cambiar_contraseña
        })
    
    def enviar_correo_confirmacion_cambio(self, usuario):
        """
        Envía correo de confirmación cuando se actualiza la contraseña
        """
        asunto = 'Contraseña actualizada exitosamente'
        
        # URL del login principal
        login_url = f"http://localhost:5173/login?email={usuario.correo_electronico}&type=usuario"
        
        mensaje_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #28a745;">✅ Contraseña actualizada exitosamente</h2>
                <p>Hola <strong>{usuario.nombre}</strong>,</p>
                <p>Te confirmamos que tu contraseña ha sido actualizada correctamente en nuestro sistema.</p>
                
                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="margin-top: 0; color: #155724;">🔐 Cambio de contraseña completado</h3>
                    <p style="margin-bottom: 0;"><strong>Fecha y hora:</strong> {usuario.updated_at.strftime('%d/%m/%Y a las %H:%M')}</p>
                    <p style="margin-bottom: 0;"><strong>Usuario:</strong> {usuario.nombre}</p>
                    <p style="margin-bottom: 0;"><strong>Correo:</strong> {usuario.correo_electronico}</p>
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
        
        Hola {usuario.nombre},
        
        Te confirmamos que tu contraseña ha sido actualizada correctamente en nuestro sistema.
        
        Ya puedes iniciar sesión con tu nueva contraseña en:
        {login_url}
        
        ¡Tu cuenta está segura!
        """
        
        send_mail(
            asunto,
            mensaje_texto,
            settings.DEFAULT_FROM_EMAIL,
            [usuario.correo_electronico],
            html_message=mensaje_html,
            fail_silently=False,
        )
            
    @action(detail=True, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request, pk=None):
        usuario = self.get_object()
        nueva_password = request.data.get('nueva_password')
        
        if not nueva_password:
            return Response(
                {"error": "Se requiere el parámetro nueva_password"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if len(nueva_password) < 6:
            return Response(
                {"error": "La contraseña debe tener al menos 6 caracteres"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        usuario.set_password(nueva_password)
        usuario.save(update_fields=['password'])
        
        return Response(
            {"mensaje": "Contraseña actualizada correctamente"}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def activar(self, request, pk=None):
        usuario = self.get_object()
        if usuario.is_active:
            return Response({"mensaje": "El usuario ya está activo."}, status=status.HTTP_200_OK)
        usuario.is_active = True
        usuario.save(update_fields=['is_active'])
        return Response({"mensaje": "Usuario activado correctamente"}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['patch'])
    def desactivar(self, request, pk=None):
        usuario = self.get_object()
        if not usuario.is_active:
            return Response({"mensaje": "El usuario ya está inactivo."}, status=status.HTTP_200_OK)
        usuario.is_active = False
        usuario.save(update_fields=['is_active'])
        return Response({"mensaje": "Usuario desactivado correctamente"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='crear-cliente')
    def crear_cliente(self, request, pk=None):
        """
        Crea un cliente a partir de un usuario existente.
        """
        try:
            usuario = self.get_object()
            
            # Verificar que el usuario tenga rol de cliente
            if not usuario.rol or usuario.rol.nombre.lower() != 'cliente':
                return Response(
                    {"error": "El usuario debe tener rol de cliente"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importar aquí para evitar importaciones circulares
            from api.clientes.models import Cliente
            from api.clientes.serializers import ClienteSerializer
            
            # Verificar si ya existe un cliente para este usuario
            if Cliente.objects.filter(usuario=usuario).exists():
                return Response(
                    {"error": "Ya existe un cliente para este usuario"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear el cliente
            cliente_data = {
                'usuario': usuario.id,
                'nombre': usuario.nombre,
                'tipo_documento': usuario.tipo_documento,
                'documento': usuario.documento,
                'celular': usuario.celular,
                'correo_electronico': usuario.correo_electronico,
                'direccion': usuario.direccion,
            }
            
            serializer = ClienteSerializer(data=cliente_data)
            if serializer.is_valid():
                cliente = serializer.save()
                return Response(
                    {
                        "mensaje": "Cliente creado exitosamente",
                        "cliente": ClienteSerializer(cliente).data
                    }, 
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": "Error al crear cliente", "detalles": serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            print(f"Error al crear cliente: {str(e)}")
            return Response(
                {"error": f"Error interno al crear cliente: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
