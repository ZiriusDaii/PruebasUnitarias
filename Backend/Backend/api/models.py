# # api/models.py

from api.abastecimientos.models import Abastecimiento
from api.categoriainsumos.models import CategoriaInsumo
from api.citas.models import Cita
from api.clientes.models import Cliente
from api.compras.models import Compra
from api.insumos.models import Insumo
from api.liquidaciones.models import Liquidacion
from api.manicuristas.models import Manicurista
from api.proveedores.models import Proveedor
from api.novedades.models import Novedad
from api.roles.models import Rol, Permiso, RolHasPermiso
from api.servicios.models import Servicio
from api.ventaservicios.models import VentaServicio 