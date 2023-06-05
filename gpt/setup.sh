python manage.py migrate --no-input
python manage.py collectstatic --no-input


export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_PASSWORD=admin
export DJANGO_SUPERUSER_EMAIL=example@email.com

python manage.py createsuperuser --noinput