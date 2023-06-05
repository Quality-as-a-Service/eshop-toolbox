python manage.py migrate --no-input
python manage.py collectstatic --no-input
DJANGO_SUPERUSER_USERNAME=$DJANGO_SUPERUSER_USERNAME \
DJANGO_SUPERUSER_PASSWORD=$DJANGO_SUPERUSER_PASSWORD \
DJANGO_SUPERUSER_EMAIL="$DJANGO_SUPERUSER_EMAIL" \
python manage.py createsuperuser --noinput