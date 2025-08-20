from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet

router = DefaultRouter()
router.register(r'', UsuarioViewSet, basename='usuario')

# URLs específicas para usuarios
usuario_login = UsuarioViewSet.as_view({
    'post': 'login'
})

usuario_cambiar_password = UsuarioViewSet.as_view({
    'post': 'cambiar_contraseña'
})

usuario_resetear_password = UsuarioViewSet.as_view({
    'post': 'resetear_contraseña'
})

urlpatterns = [
    path('', include(router.urls)),
    # Endpoints específicos para usuarios
    path('login/', usuario_login, name='usuario-login'),
    path('<int:pk>/cambiar-contraseña/', usuario_cambiar_password, name='usuario-cambiar-contraseña'),
    path('<int:pk>/resetear-contraseña/', usuario_resetear_password, name='usuario-resetear-contraseña'),
]

usuarios_urlpatterns = urlpatterns
