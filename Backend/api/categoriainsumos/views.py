from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import CategoriaInsumo
# Asumiendo que el modelo Insumo está en el mismo archivo models.py o es accesible
from api.insumos.models import Insumo # Importa el modelo Insumo
from .serializers import CategoriaInsumoSerializer # Add this import statement at the top of the file, assuming serializers.py is in the same directory


class CategoriaInsumoViewSet(viewsets.ModelViewSet):
  """
  ViewSet para manejar operaciones CRUD en Categorías de Insumos.
  """
  queryset = CategoriaInsumo.objects.all()
  serializer_class = CategoriaInsumoSerializer
  
  def get_queryset(self):
      """
      Opcionalmente filtra por estado activo o inactivo.
      """
      queryset = CategoriaInsumo.objects.all()
      estado = self.request.query_params.get('estado', None)
      nombre = self.request.query_params.get('nombre', None)
      
      if estado is not None:
          queryset = queryset.filter(estado=estado)
      
      if nombre is not None:
          queryset = queryset.filter(nombre__icontains=nombre)
          
      return queryset
  
  @action(detail=False, methods=['get'])
  def activas(self, request):
      """
      Devuelve solo las categorías activas.
      """
      categorias = CategoriaInsumo.objects.filter(estado='activo')
      serializer = self.get_serializer(categorias, many=True)
      return Response(serializer.data)
  
  @action(detail=False, methods=['get'])
  def inactivas(self, request):
      """
      Devuelve solo las categorías inactivas.
      """
      categorias = CategoriaInsumo.objects.filter(estado='inactivo')
      serializer = self.get_serializer(categorias, many=True)
      return Response(serializer.data)
  
  @action(detail=True, methods=['patch'])
  def cambiar_estado(self, request, pk=None):
      """
      Cambia el estado de la categoría (activo/inactivo).
      """
      categoria = self.get_object()
      nuevo_estado = 'inactivo' if categoria.estado == 'activo' else 'activo'
      categoria.estado = nuevo_estado
      categoria.save()
      
      serializer = self.get_serializer(categoria)
      return Response(serializer.data)

  @action(detail=True, methods=['get'])
  def check_insumos(self, request, pk=None):
      """
      Verifica si una categoría de insumo tiene insumos asociados.
      """
      categoria = self.get_object()
      # Asumiendo que 'insumos' es el related_name de Insumo a CategoriaInsumo
      # Si tu related_name es diferente, por ejemplo 'items_de_categoria', cámbialo aquí.
      insumos_count = categoria.insumos.count() 
      can_delete = insumos_count == 0

      return Response({
          'puede_eliminar': can_delete,
          'insumos_info': {'total': insumos_count},
          'categoria_nombre': categoria.nombre,
          'error_message': f"No se puede eliminar la categoría '{categoria.nombre}' porque tiene {insumos_count} insumo(s) asociado(s)." if not can_delete else None
      }, status=status.HTTP_200_OK)

  def destroy(self, request, pk=None):
      """
      Elimina una categoría de insumo, pero solo si no tiene insumos asociados.
      """
      categoria = self.get_object()
      # Asumiendo que 'insumos' es el related_name de Insumo a CategoriaInsumo
      insumos_count = categoria.insumos.count() 

      if insumos_count > 0:
          return Response(
              {
                  "error": f"No se puede eliminar la categoría '{categoria.nombre}' porque tiene {insumos_count} insumo(s) asociado(s).",
                  "detail": "Por favor, reasigne o elimine los insumos asociados a esta categoría antes de intentar eliminarla."
              },
              status=status.HTTP_400_BAD_REQUEST
          )
      return super().destroy(request, pk)
