#!/bin/bash

python manage.py migrate
python manage.py collectstatic --noinput

exec gunicorn --bind 0.0.0.0:8000 django_files.wsgi