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
