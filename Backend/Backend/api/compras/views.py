from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import F, Sum
# from django.utils import timezone # Eliminar esta importación
from .models import Compra
from .serializers import CompraSerializer, CompraCreateSerializer


class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CompraCreateSerializer
        return CompraSerializer
    
    def get_queryset(self):
        queryset = Compra.objects.all().select_related('proveedor').prefetch_related('detalles__insumo')
        
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    @action(detail=True, methods=['patch'], url_path='anular')
    def anular_compra(self, request, pk=None):
        compra = self.get_object()
        
        print("Request data recibida en anular_compra:", request.data)
        motivo_anulacion = request.data.get('motivo_anulacion', None)
        print("Motivo de anulación extraído:", motivo_anulacion)

        if compra.estado == 'anulada':
            return Response({"error": "La compra ya está anulada."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not motivo_anulacion:
            return Response({"error": "El motivo de anulación es requerido."}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(motivo_anulacion) < 10:
            return Response({"error": "El motivo de anulación debe tener al menos 10 caracteres."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Revertir stock de insumos
        for detalle in compra.detalles.all():
            insumo = detalle.insumo
            if insumo.cantidad >= detalle.cantidad:
                insumo.cantidad -= detalle.cantidad
                insumo.save()
            else:
                # Esto no debería pasar si el stock se manejó correctamente al finalizar la compra
                # Pero es una salvaguarda
                return Response(
                    {"error": f"No se pudo revertir el stock del insumo {insumo.nombre}. Cantidad insuficiente."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        compra.estado = 'anulada'
        compra.motivo_anulacion = motivo_anulacion # Guardar el motivo
        compra.save()
        
        serializer = CompraSerializer(compra)
        return Response(serializer.data, status=status.HTTP_200_OK)
