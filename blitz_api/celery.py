"""
Celery config file
https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
"""

from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blitz_api.settings')
app = Celery('blitz_api')

# Using a string here means the worker will not have to
# pickle the object when using Windows.

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'assign_retreat_tomatoes': {
        'task': 'retirement.tasks.assign_retreat_tomatoes',
        'schedule': crontab(minute=1, hour='*'),
    },
    'alert_users_of_inactivity': {
        'task': 'blitz_api.tasks.alert_users_of_inactivity',
        'schedule': crontab(minute=0, hour=9),
    },
    'disable_inactive_users': {
        'task': 'blitz_api.tasks.disable_inactive_users',
        'schedule': crontab(minute=0, hour=10),
    }
}

app.autodiscover_tasks()
