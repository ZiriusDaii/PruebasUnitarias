from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import F, Sum
from .models import Insumo
from .serializers import InsumoSerializer, InsumoDetailSerializer


class InsumoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar operaciones CRUD en Insumos.
    Proporciona endpoints para listar, crear, actualizar y eliminar insumos,
    así como acciones personalizadas para filtrar y gestionar el inventario.
    """
    queryset = Insumo.objects.all().select_related('categoria_insumo')
    
    def get_serializer_class(self):
        """
        Retorna el serializer apropiado dependiendo de la acción.
        - Para listar y ver detalles: usa InsumoDetailSerializer (incluye detalles de categoría)
        - Para otras operaciones: usa InsumoSerializer básico
        """
        if self.action in ['retrieve', 'list']:
            return InsumoDetailSerializer
        return InsumoSerializer
    
    def get_queryset(self):
        """
        Opcionalmente filtra el queryset por estado, categoría o nombre.
        Permite búsquedas y filtros a través de parámetros de consulta.
        """
        queryset = Insumo.objects.all().select_related('categoria_insumo')
        estado = self.request.query_params.get('estado', None)
        categoria = self.request.query_params.get('categoria', None)
        nombre = self.request.query_params.get('nombre', None)
        
        if estado is not None:
            queryset = queryset.filter(estado=estado)
        
        if categoria is not None:
            queryset = queryset.filter(categoria_insumo_id=categoria)
            
        if nombre is not None:
            queryset = queryset.filter(nombre__icontains=nombre)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Crea un nuevo insumo y devuelve la respuesta con el serializer detallado
        para incluir toda la información de la categoría.
        La cantidad siempre se inicializa en 0.
        """
        # Forzar cantidad a 0 para nuevos insumos
        data = request.data.copy()
        data['cantidad'] = 0
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Obtener el objeto recién creado y serializarlo con el serializer detallado
        instance = serializer.instance
        detail_serializer = InsumoDetailSerializer(instance)
        
        headers = self.get_success_headers(serializer.data)
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """
        Actualiza un insumo existente y devuelve la respuesta con el serializer detallado
        para incluir toda la información de la categoría.
        No permite modificar la cantidad directamente.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Remover cantidad de los datos si está presente para evitar modificaciones directas
        data = request.data.copy()
        if 'cantidad' in data:
            data.pop('cantidad')
        
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Serializar con el serializer detallado para incluir toda la información
        detail_serializer = InsumoDetailSerializer(instance)
        
        return Response(detail_serializer.data)
    
    @action(detail=False, methods=['get'])
    def activos(self, request):
        """
        Devuelve solo los insumos activos.
        Endpoint: /api/insumos/activos/
        """
        insumos = Insumo.objects.filter(estado='activo').select_related('categoria_insumo')
        serializer = InsumoDetailSerializer(insumos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """
        Agrupa insumos por categoría.
        Endpoint: /api/insumos/por_categoria/?id=<categoria_id>
        """
        categoria_id = request.query_params.get('id', None)
        if categoria_id:
            insumos = Insumo.objects.filter(categoria_insumo_id=categoria_id).select_related('categoria_insumo')
            serializer = InsumoDetailSerializer(insumos, many=True)
            return Response(serializer.data)
        return Response({"error": "Se requiere el ID de la categoría"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado del insumo (activo/inactivo).
        Endpoint: /api/insumos/<pk>/cambiar_estado/
        """
        insumo = self.get_object()
        nuevo_estado = 'inactivo' if insumo.estado == 'activo' else 'activo'
        insumo.estado = nuevo_estado
        insumo.save()
        
        serializer = InsumoDetailSerializer(insumo)
        return Response(serializer.data)
    
    @action(detail=True, methods=['patch'])
    def ajustar_stock(self, request, pk=None):
        """
        Ajusta la cantidad de stock del insumo.
        Endpoint: /api/insumos/<pk>/ajustar_stock/
        Parámetros:
        - cantidad: Cantidad a ajustar (positivo para aumentar, negativo para disminuir)
        """
        insumo = self.get_object()
        
        try:
            cantidad = int(request.data.get('cantidad', 0))
            if cantidad < 0 and abs(cantidad) > insumo.cantidad:
                return Response(
                    {"error": "No se puede reducir más de lo que hay en stock"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            insumo.cantidad += cantidad
            insumo.save()
            
            serializer = InsumoDetailSerializer(insumo)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {"error": "La cantidad debe ser un número entero"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
