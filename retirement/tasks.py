from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import requests


@shared_task
def assign_retreat_tomatoes():
    """
    Assign tomatoes to all active users of a retreat if one of the date passed.
    """
    from retirement.models import RetreatDate
    today = timezone.now()
    to_assign_dates = RetreatDate.objects.filter(
        end_time__lte=today,
        tomatoes_assigned=False,
    )

    for date in to_assign_dates:
        with transaction.atomic():
            active_reservations = date.retreat.reservations.filter(
                Q(is_active=True) | Q(cancelation_date__gte=date.end_time))
            for reservation in active_reservations:
                from tomato.models import Tomato
                Tomato.objects.create(
                    user=reservation.user,
                    number_of_tomato=date.number_of_tomatoes,
                    source=Tomato.TOMATO_SOURCE_RETREAT,
                    content_object=reservation,
                    acquisition_date=date.end_time,
                )
            date.tomatoes_assigned = True
            date.save()

    try:
        status_url = settings.LOCAL_SETTINGS['STATUS_URLS']['ASSIGN_RETREAT_TOMATOES']

        if status_url:
            requests.get(status_url)
    except Exception:
        # We don't want to block the task because of a status update
        # Status system should already report the error if needed
        pass