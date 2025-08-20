from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NovedadViewSet

router = DefaultRouter()
router.register(r'', NovedadViewSet, basename='novedad')

urlpatterns = [
    path('', include(router.urls)),
]

novedades__urlpatterns = urlpatterns
