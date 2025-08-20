from django.test import TestCase
from api.usuarios.models import Usuario
from api.roles.models import Rol

class Usuariotest(TestCase):

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Administrador")

    def test_create_user_basico(self):
        usuario = Usuario.objects.create_user(
            correo_electronico="ziriusdai@gmail.com",
            password="samuel12345",
            nombre="Usuario Normal",
            tipo_documento="CC",
            documento="123456789",
            celular="+12345678901",
            rol=self.rol
        )

        self.assertEqual(usuario.correo_electronico, "ziriusdai@gmail.com")
        self.assertTrue(usuario.check_password("samuel12345"))
        self.assertEqual(usuario.rol.nombre, "Administrador")

