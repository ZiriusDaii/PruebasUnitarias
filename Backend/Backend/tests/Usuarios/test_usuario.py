import pytest
from django.contrib.auth import get_user_model
from api.usuarios.models import Rol

Usuario = get_user_model()

@pytest.mark.django_db
def test_usuario_creation():
    rol = Rol.objects.create(nombre="Administrador")

    user = Usuario.objects.create_user(
        correo_electronico="test@example.com",
        nombre="Juan Pérez",
        tipo_documento="CC",
        documento="123456789",
        celular="+573001112233",
        rol=rol,
        password="password123"
    )

    assert user.correo_electronico == "test@example.com"
    assert user.nombre == "Juan Pérez"
    assert user.check_password("password123")
    assert user.is_active
    assert user.rol == rol
