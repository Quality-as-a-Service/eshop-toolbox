python manage.py migrate
python manage.py collectstatic
python manage.py createsuperuser
python manage.py shell -c "from gpt import models;models.EvaluationIteration.finish_unfinished()"