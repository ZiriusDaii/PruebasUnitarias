from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VentaServicioViewSet

router = DefaultRouter()
router.register(r'', VentaServicioViewSet, basename='ventaservicio')

urlpatterns = [
    path('', include(router.urls)),
]

ventaservicios_urlpatterns = urlpatterns