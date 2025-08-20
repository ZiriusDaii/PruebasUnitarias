from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, RegistroClienteView

urlpatterns = [
    # Rutas de autenticación básica
    path('login/', LoginView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Registro de usuarios
    path('register/cliente/', RegistroClienteView.as_view(), name='registro_cliente'),
]

auth_urlpatterns = urlpatterns