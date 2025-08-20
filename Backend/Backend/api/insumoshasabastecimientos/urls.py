from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InsumoHasAbastecimientoViewSet

router = DefaultRouter()
router.register(r'', InsumoHasAbastecimientoViewSet, basename='insumo-abastecimiento')

urlpatterns = [
    path('', include(router.urls)),
]

insumos_abastecimientos_urlpatterns = urlpatterns