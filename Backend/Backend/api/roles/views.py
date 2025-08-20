from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.apps import apps
from .models import Rol, Permiso, RolHasPermiso
from .serializers import (
    RolSerializer,
    RolDetailSerializer,
    PermisoSerializer,
    RolHasPermisoSerializer
)


class RolViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Rol.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = Rol.objects.all()

    def get_serializer_class(self):
        """
        Retorna el serializer adecuado según la acción que se esté realizando.
        """
        if self.action == 'retrieve' or self.action == 'list_detail':
            return RolDetailSerializer
        return RolSerializer

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar un rol con validación de usuarios asociados.
        """
        rol = self.get_object()

        # Verificar si es el rol Admin (protección adicional)
        if rol.nombre.lower() == 'administrador':
            return Response(
                {"error": "No se puede eliminar el rol Administrador"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si el rol tiene usuarios asociados
        usuarios_info = self.get_usuarios_info_by_rol(rol.id)

        if usuarios_info['total'] > 0:
            # Mensaje de error simplificado: solo muestra la cantidad total
            return Response(
                {
                    "error": f"No se puede eliminar el rol '{rol.nombre}' porque tiene {usuarios_info['total']} usuario(s) asociado(s). "
                            "Primero debe reasignar o eliminar los usuarios que tienen este rol."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si no hay usuarios asociados, proceder con la eliminación
        return super().destroy(request, *args, **kwargs)

    def get_usuarios_info_by_rol(self, rol_id):
        """
        Obtener información detallada de usuarios que tienen este rol asignado.
        Usa apps.get_model para evitar importaciones circulares.
        """
        info = {
            'usuarios': 0,
            'clientes': 0,
            'manicuristas': 0,
            'total': 0
        }

        try:
            # Contar usuarios generales con este rol
            try:
                Usuario = apps.get_model('usuarios', 'Usuario')
                usuarios_count = Usuario.objects.filter(rol_id=rol_id).count()
                info['usuarios'] = usuarios_count
                # print(f"Usuarios generales con rol {rol_id}: {usuarios_count}") # Comentado para reducir logs
            except Exception as e:
                print(f"Error al contar usuarios generales: {e}")

            # Contar clientes con este rol
            try:
                Cliente = apps.get_model('clientes', 'Cliente')
                # Buscar tanto por rol directo como por usuario.rol
                clientes_count = Cliente.objects.filter(
                    Q(rol_id=rol_id) | Q(usuario__rol_id=rol_id)
                ).count()
                info['clientes'] = clientes_count
                # print(f"Clientes con rol {rol_id}: {clientes_count}") # Comentado para reducir logs
            except Exception as e:
                print(f"Error al contar clientes: {e}")

            # Contar manicuristas con este rol
            try:
                Manicurista = apps.get_model('manicuristas', 'Manicurista')
                # Buscar tanto por rol directo como por usuario.rol
                manicuristas_count = Manicurista.objects.filter(
                    Q(rol_id=rol_id) | Q(usuario__rol_id=rol_id)
                ).count()
                info['manicuristas'] = manicuristas_count
                # print(f"Manicuristas con rol {rol_id}: {manicuristas_count}") # Comentado para reducir logs
            except Exception as e:
                print(f"Error al contar manicuristas: {e}")

            # Calcular total
            info['total'] = info['usuarios'] + info['clientes'] + info['manicuristas']

            # print(f"Total usuarios con rol {rol_id}: {info}") # Comentado para reducir logs
            return info

        except Exception as e:
            print(f"Error general al contar usuarios por rol: {e}")
            return info

    @action(detail=True, methods=['get'])
    def check_usuarios(self, request, pk=None):
        """
        Endpoint para verificar si un rol tiene usuarios asociados.
        """
        rol = self.get_object()
        usuarios_info = self.get_usuarios_info_by_rol(rol.id)

        return Response({
            'rol_id': rol.id,
            'rol_nombre': rol.nombre,
            'usuarios_info': usuarios_info,
            'puede_eliminar': usuarios_info['total'] == 0,
            'es_admin': rol.nombre.lower() == 'administrador'
        })

    @action(detail=False, methods=['get'])
    def list_detail(self, request):
        """
        Endpoint para listar todos los roles con información detallada.
        """
        roles = self.get_queryset()
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def activos(self, request):
        """
        Endpoint para listar solo los roles activos.
        """
        roles = self.get_queryset().filter(estado='activo')
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_permiso(self, request, pk=None):
        """
        Endpoint para añadir un permiso a un rol.
        """
        rol = self.get_object()
        permiso_id = request.data.get('permiso_id')

        if not permiso_id:
            return Response(
                {"error": "Se requiere el parámetro permiso_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            permiso = Permiso.objects.get(pk=permiso_id)
        except Permiso.DoesNotExist:
            return Response(
                {"error": "El permiso no existe"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar si ya existe la relación
        if RolHasPermiso.objects.filter(rol=rol, permiso=permiso).exists():
            return Response(
                {"error": "El rol ya tiene este permiso"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear la relación
        RolHasPermiso.objects.create(rol=rol, permiso=permiso)

        return Response(
            {"mensaje": "Permiso añadido correctamente"},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def remove_permiso(self, request, pk=None):
        """
        Endpoint para eliminar un permiso de un rol.
        """
        rol = self.get_object()
        permiso_id = request.data.get('permiso_id')

        if not permiso_id:
            return Response(
                {"error": "Se requiere el parámetro permiso_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            relacion = RolHasPermiso.objects.get(rol=rol, permiso_id=permiso_id)
            relacion.delete()
            return Response(
                {"mensaje": "Permiso eliminado correctamente"},
                status=status.HTTP_200_OK
            )
        except RolHasPermiso.DoesNotExist:
            return Response(
                {"error": "El rol no tiene este permiso"},
                status=status.HTTP_404_NOT_FOUND
            )


class PermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo Permiso.
    Proporciona operaciones CRUD completas.
    """
    queryset = Permiso.objects.all()
    serializer_class = PermisoSerializer


class RolHasPermisoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo RolHasPermiso.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = RolHasPermiso.objects.all()
    serializer_class = RolHasPermisoSerializer

    @action(detail=False, methods=['get'])
    def by_rol(self, request):
        """
        Endpoint para filtrar por rol.
        """
        rol_id = request.query_params.get('rol_id')
        if not rol_id:
            return Response(
                {"error": "Se requiere el parámetro rol_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        relaciones = self.get_queryset().filter(rol_id=rol_id)
        serializer = self.get_serializer(relaciones, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_permiso(self, request):
        """
        Endpoint para filtrar por permiso.
        """
        permiso_id = request.query_params.get('permiso_id')
        if not permiso_id:
            return Response(
                {"error": "Se requiere el parámetro permiso_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        relaciones = self.get_queryset().filter(permiso_id=permiso_id)
        serializer = self.get_serializer(relaciones, many=True)
        return Response(serializer.data)
