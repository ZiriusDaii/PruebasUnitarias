from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ManicuristaViewSet

router = DefaultRouter()
router.register(r'', ManicuristaViewSet, basename='manicurista')

# URLs específicas para manicuristas
manicurista_login = ManicuristaViewSet.as_view({
    'post': 'login'
})

manicurista_cambiar_password = ManicuristaViewSet.as_view({
    'post': 'cambiar_password'
})

manicurista_resetear_password = ManicuristaViewSet.as_view({
    'post': 'resetear_password'
})

urlpatterns = [
    path('', include(router.urls)),
    # Endpoints específicos para manicuristas
    path('manicuristas/login/', manicurista_login, name='manicurista-login'),
    path('manicuristas/<int:pk>/cambiar-password/', manicurista_cambiar_password, name='manicurista-cambiar-password'),
    path('manicuristas/<int:pk>/resetear-password/', manicurista_resetear_password, name='manicurista-resetear-password'),
]

manicuristas_urlpatterns = urlpatterns
