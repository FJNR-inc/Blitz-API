from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from blitz_api.resources import UserPersonalDataResource
import requests


@shared_task
def alert_users_of_inactivity():
    alerted_users = []

    for user in settings.AUTH_USER_MODEL.objects.filter(is_active=True):
        
        inactivity_alert_period = timezone.timedelta(
            months=59
        )

        # If user has never logged in, use date of account creation
        last_seen = user.last_login or user.date_joined
        
        # If user never logged since last alert sent, do not send another alert
        last_alert = user.last_inactivity_alert_sent
        if last_alert and last_alert > last_seen:
            continue
        
        # If user has been inactive for longer than the alert period, send alert
        if timezone.now() - last_seen > inactivity_alert_period:
            # Send alert (e.g., via email)
            user.send_inactivity_alert()
            alerted_users.append(user.email)
            
    return alerted_users


@shared_task
def disable_inactive_users():
    disabled_users = []

    for user in settings.AUTH_USER_MODEL.objects.filter(is_active=True):
        
        inactivity_disable_period = timezone.timedelta(
            years=5
        )

        # If user has never logged in, use date of account creation
        last_seen = user.last_login or user.date_joined
        
        # If user has been inactive for longer than the disable period, disable account
        if timezone.now() - last_seen > inactivity_disable_period:
            disabled_users.append(user.email)
            user.anonymise_and_disable_account()
            
    return disabled_users
