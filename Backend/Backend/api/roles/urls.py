from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RolViewSet, PermisoViewSet, RolHasPermisoViewSet

router = DefaultRouter()
router.register(r'roles', RolViewSet, basename='rol')
router.register(r'permisos', PermisoViewSet, basename='permiso')
router.register(r'roles-permisos', RolHasPermisoViewSet, basename='rol-permiso')

urlpatterns = [
    path('', include(router.urls)),
]

roles_urlpatterns = urlpatterns