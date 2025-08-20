from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q, Avg, Count
from .models import Servicio
from .serializers import ServicioSerializer
import requests
import base64

IMGBB_API_KEY = 'a41bb72c7c09866b8a25df476e47c137'

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = Servicio.objects.all()
        
        # Filtros existentes
        estado = self.request.query_params.get('estado')
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        nombre = self.request.query_params.get('nombre')
        
        # Nuevos filtros para duración
        duracion_min = self.request.query_params.get('duracion_min')
        duracion_max = self.request.query_params.get('duracion_max')
        
        # Búsqueda general (para el componente)
        search = self.request.query_params.get('search')

        if estado:
            queryset = queryset.filter(estado=estado)
        if precio_min:
            try:
                queryset = queryset.filter(precio__gte=float(precio_min))
            except ValueError:
                pass
        if precio_max:
            try:
                queryset = queryset.filter(precio__lte=float(precio_max))
            except ValueError:
                pass
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)
        if duracion_min:
            try:
                queryset = queryset.filter(duracion__gte=int(duracion_min))
            except ValueError:
                pass
        if duracion_max:
            try:
                queryset = queryset.filter(duracion__lte=int(duracion_max))
            except ValueError:
                pass
        
        # Búsqueda general en nombre y descripción
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | 
                Q(descripcion__icontains=search)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # Manejo de imagen
        image_file = request.FILES.get("imagen")
        if image_file:
            try:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

                response = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={
                        "key": IMGBB_API_KEY,
                        "image": image_data,
                        "name": image_file.name,
                    },
                    timeout=30  # Timeout para evitar cuelgues
                )

                if response.status_code == 200:
                    image_url = response.json()["data"]["url"]
                    data["imagen"] = image_url
                else:
                    return Response(
                        {"error": "Error al subir imagen a ImgBB", "details": response.text},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            except requests.RequestException as e:
                return Response(
                    {"error": "Error de conexión al subir imagen", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except Exception as e:
                return Response(
                    {"error": "Error inesperado al procesar imagen", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Manejo de PUT o PATCH con soporte para nueva imagen"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data.copy()

        # Manejo de imagen (solo si se envía una nueva)
        image_file = request.FILES.get("imagen")
        if image_file:
            try:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

                response = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={
                        "key": IMGBB_API_KEY,
                        "image": image_data,
                        "name": image_file.name,
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    image_url = response.json()["data"]["url"]
                    data["imagen"] = image_url
                else:
                    return Response(
                        {"error": "Error al subir imagen a ImgBB", "details": response.text},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            except requests.RequestException as e:
                return Response(
                    {"error": "Error de conexión al subir imagen", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except Exception as e:
                return Response(
                    {"error": "Error inesperado al procesar imagen", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def activos(self, request):
        """Obtener solo servicios activos"""
        servicios = Servicio.objects.filter(estado='activo')
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def inactivos(self, request):
        """Obtener solo servicios inactivos"""
        servicios = Servicio.objects.filter(estado='inactivo')
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado de un servicio"""
        servicio = self.get_object()
        nuevo_estado = 'inactivo' if servicio.estado == 'activo' else 'activo'
        servicio.estado = nuevo_estado
        servicio.save()
        serializer = self.get_serializer(servicio)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_precio(self, request):
        """Ordenar servicios por precio"""
        orden = request.query_params.get('orden', 'asc')
        servicios = Servicio.objects.all().order_by('precio' if orden == 'asc' else '-precio')
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_duracion(self, request):
        """Ordenar servicios por duración"""
        orden = request.query_params.get('orden', 'asc')
        servicios = Servicio.objects.all().order_by('duracion' if orden == 'asc' else '-duracion')
        serializer = self.get_serializer(servicios, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de servicios"""
        total_servicios = Servicio.objects.count()
        servicios_activos = Servicio.objects.filter(estado='activo').count()
        servicios_inactivos = Servicio.objects.filter(estado='inactivo').count()
        
        # Estadísticas de precios
        precios_stats = Servicio.objects.aggregate(
            precio_promedio=Avg('precio'),
            precio_min=models.Min('precio'),
            precio_max=models.Max('precio')
        )
        
        # Estadísticas de duración
        duracion_stats = Servicio.objects.aggregate(
            duracion_promedio=Avg('duracion'),
            duracion_min=models.Min('duracion'),
            duracion_max=models.Max('duracion')
        )

        return Response({
            'total_servicios': total_servicios,
            'servicios_activos': servicios_activos,
            'servicios_inactivos': servicios_inactivos,
            'precios': precios_stats,
            'duracion': duracion_stats
        })

    @action(detail=False, methods=['get'])
    def top_vendidos(self, request):
        """Obtener servicios más vendidos"""
        try:
            from ventaservicios.models import VentaServicio
            from django.db.models import Case, When, IntegerField

            limit = int(request.query_params.get('limit', 5))

            servicios_ids = VentaServicio.objects.values('servicio') \
                .annotate(total=Count('servicio')) \
                .order_by('-total')[:limit] \
                .values_list('servicio', flat=True)

            order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(servicios_ids)],
                         output_field=IntegerField())

            servicios = Servicio.objects.filter(pk__in=servicios_ids).order_by(order)
            serializer = self.get_serializer(servicios, many=True)
            return Response(serializer.data)
        except ImportError:
            # Si no existe el modelo VentaServicio, retornar servicios activos
            servicios = Servicio.objects.filter(estado='activo')[:5]
            serializer = self.get_serializer(servicios, many=True)
            return Response(serializer.data)
