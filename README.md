# Proyecto Pruebas Unitarias

## Descripción

Este proyecto es un sistema backend desarrollado en Django para las pruebas basicas unitarias de:
Manicuristas,
clientes,
roles,
clientes,
novedades,
para asegurar la calidad y correcto funcionamiento de los modelos de negocio implementados hasta la fecha.

## Requisitos previos

-visual estudio 
- Python 3.8 o superior
- Django 4.x (según tu configuración)
- Base de datos MySQL
- Configurar el .env con tu configuracion

## Comandos para inicializar el proyecto

### intalar requerimientos
- pip install -r requirements.txt
### hacer las migraciones
- python manage.py makemigrations

- python manage.py migrate

## COMANDOS PARA HACER LAS 5 PRUEBAS


- python manage.py test api.tests.test_roles
  
- python manage.py test api.tests.test_cliente

- python manage.py test api.tests.test_manicurista

- python manage.py test api.tests.test_novedades

- python manage.py test api.tests.test_usuarios
