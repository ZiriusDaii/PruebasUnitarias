from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet

router = DefaultRouter()
router.register(r'', ClienteViewSet, basename='cliente')

# URLs específicas para clientes
cliente_login = ClienteViewSet.as_view({
    'post': 'login'
})

cliente_cambiar_password = ClienteViewSet.as_view({
    'post': 'cambiar_password'
})

cliente_resetear_password = ClienteViewSet.as_view({
    'post': 'resetear_password'
})

urlpatterns = [
    path('', include(router.urls)),
    # Endpoints específicos para clientes
    path('clientes/login/', cliente_login, name='cliente-login'),
    path('clientes/<int:pk>/cambiar-password/', cliente_cambiar_password, name='cliente-cambiar-password'),
    path('clientes/<int:pk>/resetear-password/', cliente_resetear_password, name='cliente-resetear-password'),
]

clientes_urlpatterns = urlpatterns
