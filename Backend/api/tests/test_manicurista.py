import unittest
from django.test import TestCase
from api.roles.models import Rol
from api.manicuristas.models import Manicurista  # Ajusta la ruta según tu proyecto

class ManicuristaTest(TestCase):

    def setUp(self):
        self.rol = Rol.objects.create(nombre="Manicurista")

    def test_creacion_manicurista(self):
        manicurista = Manicurista.objects.create(
            nombre="Ana María Pérez",
            tipo_documento="CC",
            numero_documento="123456789",
            especialidad="Manicure Clásica",
            celular="+12345678901",
            correo="ana@example.com",
            estado="activo"
        )
        self.assertEqual(manicurista.nombre, "Ana María Pérez")
        self.assertEqual(manicurista.especialidad, "Manicure Clásica")
        self.assertEqual(manicurista.estado, "activo")
        self.assertTrue(manicurista.disponible)

    def test_propiedades_nombres_apellidos(self):
        manicurista = Manicurista(nombre="Ana María Pérez")
        self.assertEqual(manicurista.nombres, "Ana")
        self.assertEqual(manicurista.apellidos, "María Pérez")

        manicurista.nombre = "Ana"
        self.assertEqual(manicurista.nombres, "Ana")
        self.assertEqual(manicurista.apellidos, "")

    def test_contraseña_temporal_y_cambio(self):
        manicurista = Manicurista(nombre="Carlos López")
        manicurista.save()  # Guardar para evitar error
        contraseña_temp = manicurista.generar_contraseña_temporal()
        self.assertTrue(manicurista.debe_cambiar_contraseña)
        self.assertTrue(manicurista.verificar_contraseña_temporal(contraseña_temp))
        self.assertFalse(manicurista.verificar_contraseña_temporal("clave_incorrecta"))

        manicurista.cambiar_contraseña("nueva_clave123")
        self.assertFalse(manicurista.debe_cambiar_contraseña)
        self.assertTrue(manicurista.verificar_contraseña_temporal("nueva_clave123"))



if __name__ == '__main__':
    unittest.main()
