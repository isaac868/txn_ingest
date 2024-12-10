#!/bin/bash

python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic

exec gunicorn --bind 0.0.0.0:8000 django_files.wsgi