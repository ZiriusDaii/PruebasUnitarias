from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProveedorViewSet

router = DefaultRouter()
router.register(r'', ProveedorViewSet, basename='proveedor')

urlpatterns = [
    path('', include(router.urls)),
]

proveedores__urlpatterns = urlpatterns