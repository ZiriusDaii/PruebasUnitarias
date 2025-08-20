from django.urls import path, include

urlpatterns = [
    path('abastecimientos/', include('api.abastecimientos.urls')),
    path('auth/', include('api.authentication.urls')),
    path('categoria-insumos/', include('api.categoriainsumos.urls')),
    path('citas/', include('api.citas.urls')),
    path('clientes/', include('api.clientes.urls')), # Esto incluirá todas las URLs definidas en __init__.py
    path('codigo-recuperacion/', include('api.codigorecuperacion.urls')), 
    path('compra-insumo/', include('api.comprahasinsumos.urls')), 
    path('compras/', include('api.compras.urls')), 
    path('insumos/', include('api.insumos.urls')), 
    path('insumo-abastecimiento/', include('api.insumoshasabastecimientos.urls')),
    path('liquidaciones/', include('api.liquidaciones.urls')), 
    path('manicuristas/', include('api.manicuristas.urls')),
    path('novedades/', include('api.novedades.urls')),  
    path('proveedores/', include('api.proveedores.urls')), 
    path('roles/', include('api.roles.urls')),
    path('servicios/', include('api.servicios.urls')), 
    path('usuarios/', include('api.usuarios.urls')),
    path('venta-servicios/', include('api.ventaservicios.urls')), 
]