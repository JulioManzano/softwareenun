python -m venv venv
source venv/bin/activate    # Linux/Mac
venv\Scripts\activate       # Windows

pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py runserver
python manage.py shell

python manage.py createsuperuser

pip freeze > requirements.txt

from script.auto_assign_delivery import run, clear
clear()
run()

## Firebase Auth para herramientas cloud

Instalar `requirements.txt` y definir `FIREBASE_PROJECT_ID` junto con Application
Default Credentials (`GOOGLE_APPLICATION_CREDENTIALS` apunta a un archivo privado
fuera del repositorio, o usar credenciales del entorno). Aplicar `core.0003` con
`python manage.py migrate` antes de habilitar tráfico autenticado.

GraphQL acepta `Authorization: Bearer <firebase_id_token>` y valida firma,
proyecto, expiración y revocación con Firebase Admin. Sin encabezado, las queries
públicas siguen disponibles. `me` exige token Firebase válido; expone únicamente
id, firebase_uid, email y email_verified del usuario actual.

La primera petición válida crea `core.User` exclusivamente por `firebase_uid`,
con username único y contraseña inutilizable. Email es opcional y no único; no se
vinculan identidades por email. Cuentas inactivas, eliminadas o bloqueadas se rechazan.
Para nuevos resolvers cloud usar `@firebase_required` de
`core.services.firebase_auth` y filtrar datos por `info.context.user`; el guard de
Flutter no reemplaza la autorización del servidor.

Pruebas: `python manage.py test core.test_firebase_auth` (Firebase Admin simulado,
sin credenciales reales). La configuración OAuth y la validación real de los
proveedores se documentan en `vtv_all/docs/firebase-auth.md` del frontend.
