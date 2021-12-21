"""
Celery config file
https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html
"""

from __future__ import absolute_import
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'blitz_api.settings')
app = Celery('blitz_api')

# Using a string here means the worker will not have to
# pickle the object when using Windows.

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    # Add some schedule tasks here if you need
}

app.autodiscover_tasks()
