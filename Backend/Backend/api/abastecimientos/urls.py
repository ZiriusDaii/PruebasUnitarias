from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AbastecimientoViewSet

router = DefaultRouter()
router.register(r'', AbastecimientoViewSet, basename='abastecimiento')

urlpatterns = [
    path('', include(router.urls)),
]

abastecimientos_urlpatterns = urlpatterns