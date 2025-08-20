from rest_framework import viewsets, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend

from .models import Abastecimiento
from .serializers import AbastecimientoSerializer, AbastecimientoDetailSerializer
from api.manicuristas.models import Manicurista


class AbastecimientoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar operaciones CRUD de Abastecimientos.
    
    Este ViewSet proporciona endpoints para listar, crear, actualizar y eliminar
    registros de abastecimientos de insumos a manicuristas.
    """
    queryset = Abastecimiento.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['fecha', 'manicurista']
    search_fields = ['manicurista__nombre']
    ordering_fields = ['fecha', 'cantidad']
    ordering = ['-fecha']  # Ordenamiento por defecto: fechas más recientes primero
    
    def get_serializer_class(self):
        """
        Retorna el serializer adecuado según la acción.
        - Para listado y detalle: AbastecimientoDetailSerializer
        - Para crear y actualizar: AbastecimientoSerializer
        """
        if self.action in ['list', 'retrieve']:
            return AbastecimientoDetailSerializer
        return AbastecimientoSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Obtenemos el objeto recién creado con el serializer de detalle
        abastecimiento = Abastecimiento.objects.get(pk=serializer.data['id'])
        detail_serializer = AbastecimientoDetailSerializer(abastecimiento)
        
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Obtenemos el objeto actualizado con el serializer de detalle
        abastecimiento = Abastecimiento.objects.get(pk=instance.id)
        detail_serializer = AbastecimientoDetailSerializer(abastecimiento)
        
        return Response(detail_serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_manicurista(self, request):
        """
        Obtiene los abastecimientos filtrados por manicurista.
        
        Parámetros de consulta:
        - manicurista_id: ID de la manicurista
        """
        manicurista_id = request.query_params.get('manicurista_id')
        if not manicurista_id:
            return Response(
                {"error": "Debe proporcionar un ID de manicurista"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            manicurista = Manicurista.objects.get(pk=manicurista_id)
        except Manicurista.DoesNotExist:
            return Response(
                {"error": "La manicurista especificada no existe"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        abastecimientos = Abastecimiento.objects.filter(manicurista=manicurista)
        serializer = AbastecimientoDetailSerializer(abastecimientos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_periodo(self, request):
        """
        Obtiene los abastecimientos en un período específico.
        
        Parámetros de consulta:
        - fecha_inicio: Fecha de inicio (formato YYYY-MM-DD)
        - fecha_fin: Fecha de fin (formato YYYY-MM-DD)
        """
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            return Response(
                {"error": "Debe proporcionar fecha_inicio y fecha_fin"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        abastecimientos = Abastecimiento.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        )
        
        serializer = AbastecimientoDetailSerializer(abastecimientos, many=True)
        return Response(serializer.data)