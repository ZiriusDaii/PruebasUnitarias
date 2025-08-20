import unittest
from django.test import TestCase
from api.roles.models import Rol, Permiso, RolHasPermiso

class RolesTest(TestCase):

    def setUp(self):
        # Crear permisos de prueba
        self.permiso1 = Permiso.objects.create(nombre="Ver Dashboard")
        self.permiso2 = Permiso.objects.create(nombre="Editar Usuario")

    def test_creacion_permiso(self):
        self.assertEqual(self.permiso1.nombre, "Ver Dashboard")
        self.assertEqual(self.permiso1.estado, "activo")

    def test_creacion_rol(self):
        rol = Rol.objects.create(nombre="Administrador")
        self.assertEqual(rol.nombre, "Administrador")
        self.assertEqual(rol.estado, "activo")
        self.assertEqual(rol.permisos.count(), 0)  # Sin permisos aún

    def test_asignar_permisos_a_rol(self):
        rol = Rol.objects.create(nombre="Editor")
        # Asignar permisos usando relación ManyToMany
        rol.permisos.add(self.permiso1, self.permiso2)
        self.assertEqual(rol.permisos.count(), 2)
        self.assertIn(self.permiso1, rol.permisos.all())
        self.assertIn(self.permiso2, rol.permisos.all())

        # Verificar tabla intermedia RolHasPermiso
        rel = RolHasPermiso.objects.filter(rol=rol, permiso=self.permiso1).exists()
        self.assertTrue(rel)

if __name__ == '__main__':
    unittest.main()
