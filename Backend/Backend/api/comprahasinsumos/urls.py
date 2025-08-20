from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompraHasInsumoViewSet

router = DefaultRouter()
router.register(r'', CompraHasInsumoViewSet, basename='compra-insumo')

urlpatterns = [
    path('', include(router.urls)),
]

compras_insumo_urlpatterns = urlpatterns
