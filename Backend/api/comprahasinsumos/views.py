from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import CompraHasInsumo
from .serializers import CompraHasInsumoSerializer, CompraHasInsumoDetailSerializer


class CompraHasInsumoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para el modelo CompraHasInsumo.
    Proporciona operaciones CRUD completas y algunos endpoints adicionales.
    """
    queryset = CompraHasInsumo.objects.all()
    
    def get_serializer_class(self):
        """
        Retorna el serializer adecuado según la acción que se esté realizando.
        """
        if self.action == 'retrieve' or self.action == 'list_detail':
            return CompraHasInsumoDetailSerializer
        return CompraHasInsumoSerializer
    
    @action(detail=False, methods=['get'])
    def list_detail(self, request):
        """
        Endpoint para listar todos los registros con información detallada.
        """
        registros = self.get_queryset()
        serializer = self.get_serializer(registros, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_compra(self, request):
        """
        Endpoint para filtrar por compra.
        """
        compra_id = request.query_params.get('compra_id')
        if not compra_id:
            return Response(
                {"error": "Se requiere el parámetro compra_id"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registros = self.get_queryset().filter(compra_id=compra_id)
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
    
    @action(detail=False, methods=['get'])
    def top_insumos(self, request):
        """
        Endpoint para obtener los insumos más comprados.
        """
        limit = request.query_params.get('limit', 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
            
        top_insumos = (
            CompraHasInsumo.objects
            .values('insumo', 'insumo__nombre')
            .annotate(total_comprado=Sum('cantidad'))
            .order_by('-total_comprado')[:limit]
        )
        
        return Response(top_insumos)
