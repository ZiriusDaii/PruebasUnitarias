from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Proveedor
from .serializers import ProveedorSerializer


class ProveedorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar operaciones CRUD en Proveedores.
    """
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    
    def get_queryset(self):
        """
        Opcionalmente filtra por estado activo o inactivo.
        """
        queryset = Proveedor.objects.all()
        estado = self.request.query_params.get('estado', None)
        if estado is not None:
            queryset = queryset.filter(estado=estado)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Crear un nuevo proveedor. Si no se especifica estado, se asigna 'activo' por defecto.
        """
        if 'estado' not in request.data:
            request.data['estado'] = 'activo'
        return super().create(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """
        Devuelve solo los proveedores activos.
        """
        proveedores = Proveedor.objects.filter(estado='activo')
        serializer = self.get_serializer(proveedores, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def inactivos(self, request):
        """
        Devuelve solo los proveedores inactivos.
        """
        proveedores = Proveedor.objects.filter(estado='inactivo')
        serializer = self.get_serializer(proveedores, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado del proveedor (activo/inactivo).
        """
        proveedor = self.get_object()
        nuevo_estado = 'inactivo' if proveedor.estado == 'activo' else 'activo'
        proveedor.estado = nuevo_estado
        proveedor.save()
        
        serializer = self.get_serializer(proveedor)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def activar(self, request, pk=None):
        """
        Activa un proveedor específico.
        """
        proveedor = self.get_object()
        proveedor.estado = 'activo'
        proveedor.save()
        
        serializer = self.get_serializer(proveedor)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def desactivar(self, request, pk=None):
        """
        Desactiva un proveedor específico.
        """
        proveedor = self.get_object()
        proveedor.estado = 'inactivo'
        proveedor.save()
        
        serializer = self.get_serializer(proveedor)
        return Response(serializer.data)