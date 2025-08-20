from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
import logging

from api.usuarios.models import Usuario
from api.manicuristas.models import Manicurista
from api.clientes.models import Cliente
from api.roles.models import Rol

from api.usuarios.serializers import (
    UsuarioSerializer,
    UsuarioDetailSerializer
)
from api.clientes.serializers import ClienteSerializer

logger = logging.getLogger(__name__)


# ✅ LOGIN personalizado con JWT y campos adicionales
class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data.copy()
        login_input = data.get('correo_electronico')

        if login_input:
            try:
                user = Usuario.objects.filter(correo_electronico=login_input).first()
                if user:
                    data['username'] = user.correo_electronico
            except Exception as e:
                logger.error(f"Error al buscar usuario por correo: {e}")
                return Response({"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                return Response({"detail": "No active account found with the given credentials"}, status=401)


        # Continuar con el login original
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            try:
                user = Usuario.objects.get(correo_electronico=login_input or data.get('username'))

                # Adjuntar objeto `user` serializado
                usuario_serializado = UsuarioDetailSerializer(user)
                response.data['user'] = usuario_serializado.data

                # Roles específicos
                if hasattr(user, 'rol') and user.rol:
                    if user.rol.nombre.lower() == 'cliente':
                        try:
                            cliente = Cliente.objects.get(documento=user.documento)
                            response.data['cliente_id'] = cliente.id
                        except Cliente.DoesNotExist:
                            logger.warning(f"No se encontró cliente para el usuario {user.correo_electronico}")
                    elif user.rol.nombre.lower() == 'manicurista':
                        try:
                            nombre_split = user.nombre.split()
                            if nombre_split:
                                manicurista = Manicurista.objects.filter(nombres=nombre_split[0]).first()
                                if manicurista:
                                    response.data['manicurista_id'] = manicurista.id
                        except Exception as e:
                            logger.warning(f"No se encontró manicurista para el usuario {user.correo_electronico}: {e}")
            except Exception as e:
                logger.error(f"Error al obtener info del usuario tras login: {e}")

        return response


# ✅ REGISTRO de usuario (cliente) + generación de tokens y respuesta esperada por frontend
class RegistroClienteView(generics.CreateAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            rol_cliente = Rol.objects.get(nombre__iexact='cliente')
        except Rol.DoesNotExist:
            return Response({"error": "El rol de cliente no existe en el sistema"}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data['rol'] = rol_cliente.id

        usuario_serializer = self.get_serializer(data=data)
        if not usuario_serializer.is_valid():
            return Response(usuario_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = usuario_serializer.save()

        cliente_data = {
            'tipo_documento': usuario.tipo_documento,
            'documento': usuario.documento,
            'nombre': usuario.nombre,
            'celular': usuario.celular,
            'correo_electronico': usuario.correo_electronico,
            'direccion': usuario.direccion
        }

        cliente_serializer = ClienteSerializer(data=cliente_data)
        if cliente_serializer.is_valid():
            cliente = cliente_serializer.save()
        else:
            usuario.delete()
            return Response({
                "error": "No se pudo crear el perfil de cliente",
                "details": cliente_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # ✅ GENERAR JWT
        refresh = RefreshToken.for_user(usuario)
        access = str(refresh.access_token)

        # ✅ Serializar usuario
        usuario_serializado = UsuarioDetailSerializer(usuario)

        # ✅ RESPUESTA esperada por frontend
        return Response({
            "access": access,
            "refresh": str(refresh),
            "user": usuario_serializado.data
        }, status=status.HTTP_201_CREATED)


# ✅ LOGOUT: invalidar token
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response({"error": "Se requiere el token de actualización para cerrar sesión"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"mensaje": "Sesión cerrada correctamente"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error al cerrar sesión: {e}")
            return Response({"error": f"Error al cerrar sesión: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
