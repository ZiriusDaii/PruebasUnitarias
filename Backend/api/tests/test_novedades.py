import unittest
from datetime import date, timedelta, time
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from api.manicuristas.models import Manicurista
from api.novedades.models import Novedad


class NovedadTest(TestCase):

    def setUp(self):
        self.manicurista = Manicurista.objects.create(nombre="Ana Pérez")
        self.hoy = timezone.now().date()
        self.manana = self.hoy + timedelta(days=1)

    def test_creacion_novedad_valida(self):
        novedad = Novedad.objects.create(
            manicurista=self.manicurista,
            fecha=self.manana,
            estado='ausente',
            tipo_ausencia='completa',
            hora_entrada=None,
            hora_salida=None
        )
        self.assertEqual(novedad.estado, 'ausente')
        self.assertEqual(novedad.tipo_ausencia, 'completa')
        self.assertEqual(novedad.fecha, self.manana)

    

if __name__ == '__main__':
    unittest.main()
