from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import InsumoHasAbastecimiento
from .serializers import (
    InsumoHasAbastecimientoSerializer,
    InsumoHasAbastecimientoDetailSerializer
)


class InsumoHasAbastecimientoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo InsumoHasAbastecimiento.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = InsumoHasAbastecimiento.objects.all()
    
    def get_serializer_class(self):
        """
        Retorna el serializer adecuado según la acción que se esté realizando.
        """
        if self.action == 'retrieve' or self.action == 'list_detail':
            return InsumoHasAbastecimientoDetailSerializer
        return InsumoHasAbastecimientoSerializer
    
    @action(detail=False, methods=['get'])
    def list_detail(self, request):
        """
        Endpoint para listar todos los registros con información detallada.
        """
        registros = self.get_queryset()
        serializer = self.get_serializer(registros, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_abastecimiento(self, request):
        """
        Endpoint para filtrar por abastecimiento.
        """
        abastecimiento_id = request.query_params.get('abastecimiento_id')
        if not abastecimiento_id:
            return Response(
                {"error": "Se requiere el parámetro abastecimiento_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registros = self.get_queryset().filter(abastecimiento_id=abastecimiento_id)
        serializer = self.get_serializer(registros, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_insumo(self, request):
        """
        Endpoint para filtrar por insumo.
        """
        insumo_id = request.query_params.get('insumo_id')
        if not insumo_id:
            return Response(
                {"error": "Se requiere el parámetro insumo_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registros = self.get_queryset().filter(insumo_id=insumo_id)
        serializer = self.get_serializer(registros, many=True)
        return Response(serializer.data)
