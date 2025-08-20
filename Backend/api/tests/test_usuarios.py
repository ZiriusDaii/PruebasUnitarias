import unittest
from django.test import TestCase
from api.usuarios.models import Usuario
from api.roles.models import Rol

class UsuarioTest(TestCase):

    def setUp(self):
        # Aquí preparamos datos comunes para los tests
        self.rol = Rol.objects.create(nombre="Administrador")

    def test_creacion_usuario(self):
        usuario = Usuario.objects.create_user(
            correo_electronico="user@example.com",
            password="pass1234",
            nombre="Usuario Ejemplo",
            tipo_documento="CC",
            documento="123456789",
            celular="+12345678901",
            rol=self.rol
        )
        self.assertEqual(usuario.correo_electronico, "user@example.com")
        self.assertTrue(usuario.check_password("pass1234"))

if __name__ == '__main__':
    unittest.main()
