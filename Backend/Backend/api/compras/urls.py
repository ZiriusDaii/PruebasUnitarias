from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompraViewSet

router = DefaultRouter()
# Registrar sin prefijo adicional ya que el prefijo se maneja en __init__.py
router.register(r'', CompraViewSet, basename='compra')

urlpatterns = [
    path('', include(router.urls)),
]

compras_urlpatterns = urlpatterns
