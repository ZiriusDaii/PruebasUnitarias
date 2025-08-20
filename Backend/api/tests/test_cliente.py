import unittest
from django.test import TestCase
from api.roles.models import Rol
from api.clientes.models import Cliente  # Ajusta la ruta según tu proyecto

class ClienteTest(TestCase):

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Cliente")

    def test_creacion_cliente(self):
        cliente = Cliente.objects.create(
            tipo_documento="CC",
            documento="123456789",
            nombre="Juan Pérez",
            celular="+12345678901",
            correo_electronico="juan@example.com",
            direccion="Calle Falsa 123",
            estado=True,
            genero="M"
        )
        self.assertEqual(cliente.nombre, "Juan Pérez")
        self.assertEqual(cliente.documento, "123456789")
        self.assertEqual(cliente.genero, "M")
        self.assertTrue(cliente.estado)

    def test_generar_verificar_contraseña_temporal(self):
        cliente = Cliente(nombre="Adriana López")
        cliente.save()  # Guardar para evitar error de pk
        contraseña_temp = cliente.generar_contraseña_temporal()
        self.assertTrue(cliente.debe_cambiar_contraseña)
        self.assertTrue(cliente.verificar_contraseña_temporal(contraseña_temp))
        self.assertFalse(cliente.verificar_contraseña_temporal("contraseña_incorrecta"))

    def test_cambiar_contraseña(self):
        cliente = Cliente(nombre="Luis Gómez")
        cliente.save()
        cliente.generar_contraseña_temporal()
        cliente.cambiar_contraseña("nueva_clave456")
        self.assertFalse(cliente.debe_cambiar_contraseña)
        self.assertTrue(cliente.verificar_contraseña_temporal("nueva_clave456"))


if __name__ == '__main__':
    unittest.main()
