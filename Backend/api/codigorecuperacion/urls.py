from django.urls import path
from .views import SolicitarCodigoRecuperacionView, ConfirmarCodigoRecuperacionView

urlpatterns = [
    path('solicitar-codigo/', SolicitarCodigoRecuperacionView.as_view(), name='solicitar_codigo'),
    path('confirmar-codigo/', ConfirmarCodigoRecuperacionView.as_view(), name='confirmar_codigo'),
]

recuperacion_urlpatterns = urlpatterns