from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CitaViewSet

router = DefaultRouter()
router.register(r'', CitaViewSet, basename='cita')

urlpatterns = [
    path('', include(router.urls)),
]

citas_urlpatterns = urlpatterns
