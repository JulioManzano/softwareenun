# Instrucciones del backend Django

## Arquitectura actual

- El proyecto usa Django con las apps `core` y `channel`, configuración en `config/` y punto de entrada `manage.py`.
- Los modelos están en `core/models.py` y `channel/models.py`; las migraciones están en las carpetas `migrations/` de cada app.
- La lógica reutilizable se organiza en servicios, incluidos `core/services/`, `core/downloader/` y `channel/services/`.
- Los filtros están en `core/filters.py` y `channel/filters.py`; las vistas HTTP y URLs existentes deben conservar sus contratos.
- El acceso a datos usa el ORM de Django. La configuración permite PostgreSQL mediante `DATABASE_URL` y tiene SQLite como fallback local; no cambiar esta estrategia sin una decisión explícita.

## Graphene GraphQL

- GraphQL se expone desde `config/urls.py` mediante Graphene y `graphene-file-upload`; las queries y mutaciones se componen desde `core/scheme.py` y `channel/scheme.py`.
- Los tipos GraphQL están junto a cada app (`core/types.py` y `channel/types.py`) y usan `graphene-django`/`graphene-django-extras`.
- Mantener todos los nombres públicos de GraphQL en `snake_case`. La configuración actual usa `auto_camelcase=False`; no activarla ni introducir nombres camelCase.
- Antes de cambiar una query, mutación, argumento, campo, filtro o tipo, revisar el esquema y todos los consumidores del frontend.
- Validar entradas, límites, existencia de objetos y errores de forma consistente con el patrón existente; no devolver trazas, secretos ni detalles internos al cliente.
- Evitar N+1 queries. Usar `select_related`, `prefetch_related`, anotaciones o consultas equivalentes cuando corresponda, especialmente en relaciones y campos resolvers.

## Seguridad y autorización

- Validar autenticación, permisos y roles antes de exponer, crear, modificar o eliminar datos. No asumir que un `user_id` recibido como parámetro equivale a un usuario autenticado.
- Revisar los permisos existentes en `info.context`, vistas y servicios antes de agregar una operación pública.
- Mantener secretos, tokens, claves API, credenciales, datos de producción y archivos `.env` fuera del repositorio. Usar variables de entorno y `.env.example` sin valores reales.
- No registrar tokens, archivos completos, URLs firmadas ni información sensible. Preferir logging estructurado y niveles apropiados.

## Modelos y migraciones

- Usar migraciones de Django para cualquier cambio de modelos, relaciones, índices o restricciones.
- No editar migraciones ya aplicadas en producción; crear una nueva migración compatible y revisar su impacto.
- Preservar restricciones, `related_name`, nombres públicos y compatibilidad de datos existentes.
- Para cambios potencialmente destructivos, preparar una migración segura y solicitar confirmación antes de ejecutarlos.

## Comandos y validación

- Comandos documentados en `readme.md`: `python -m venv venv`, activar el entorno, `pip install -r requirements.txt`, `python manage.py makemigrations`, `python manage.py migrate`, `python manage.py runserver`, `python manage.py shell`, `python manage.py createsuperuser` y `pip freeze > requirements.txt`.
- Antes de modificar modelos, revisar migraciones y ejecutar `python manage.py makemigrations` solo cuando corresponda; no crear migraciones por cambios que no sean de esquema.
- Ejecutar `python manage.py check` y `python manage.py test` como validaciones Django cuando el entorno y el alcance lo permitan.
- Ejecutar las pruebas existentes y validaciones específicas de GraphQL o servicios afectados cuando estén disponibles.
- Revisar el diff y el estado de Git; no incluir `.env`, bases de datos locales, media ni artefactos generados.
