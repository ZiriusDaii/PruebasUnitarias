from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoriaInsumoViewSet

router = DefaultRouter()
router.register(r'', CategoriaInsumoViewSet, basename='categoria-insumo')

urlpatterns = [
    path('', include(router.urls)),
]

categoriainsumos_urlpatterns = urlpatterns