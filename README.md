# Orbit Eats

Base de datos, API y GUI para un restaurante de delivery (proyecto de Bases de Datos).
Autores: Javier Herdoiza, Ismael Cifuentes.

## Estructura

```
orbit_eats_schema.sql   tablas, llaves y restricciones (MySQL 8)
orbit_eats_tests.sql    datos de ejemplo + casos de prueba SQL (TC-01 a TC-08)
api/app.py              API REST con Flask + SQLAlchemy
api/test_api.py         casos de prueba de la API (incluye TC-09 y TC-10)
api/static/index.html   GUI (se abre en http://127.0.0.1:8000)
docs/                   documento de diseño (PDF)
```

## Cómo levantarlo

1. MySQL en Docker (con volumen y reinicio automático, NFR-03):

   ```
   docker volume create orbit_data
   docker run --name orbit-mysql -d -p 3306:3306 -e MYSQL_ROOT_PASSWORD=change-me -v orbit_data:/var/lib/mysql --restart unless-stopped mysql:8.0.33
   ```

2. Crear las tablas y cargar los datos de ejemplo:

   ```
   docker exec -i orbit-mysql mysql -uroot -pchange-me < orbit_eats_schema.sql
   docker exec -i orbit-mysql mysql -uroot -pchange-me --force < orbit_eats_tests.sql
   ```

3. Instalar dependencias y arrancar la API:

   ```
   cd api
   pip install -r requirements.txt
   python app.py
   ```

4. Abrir http://127.0.0.1:8000 (GUI) o correr las pruebas en otra terminal: `python test_api.py`

## Endpoints

Todas las rutas piden el encabezado `Authorization: Bearer token-secreto-123`.

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET / POST | `/customers`, `/employees`, `/products`, `/ingredients`, `/suppliers`, `/supplies` | Listar / crear |
| GET / PUT / DELETE | `/<recurso>/<id>` | Ver / actualizar / eliminar |
| GET / POST | `/orders` | Listar (filtro `?status=`) / crear pedido con sus productos |
| GET / PATCH / DELETE | `/orders/<id>` | Ver / cambiar estado o repartidor / cancelar |
| GET / POST | `/products/<id>/recipe` | Ver / agregar ingrediente a la receta |
| GET | `/ingredients/low-stock` | Ingredientes bajo el mínimo |
| GET | `/ingredients/<id>/suppliers` | Proveedores de un ingrediente |
