from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LiquidacionViewSet

router = DefaultRouter()
router.register(r'', LiquidacionViewSet, basename='liquidacion')

urlpatterns = [
    path('', include(router.urls)),
]

liquidaciones__urlpatterns = urlpatterns