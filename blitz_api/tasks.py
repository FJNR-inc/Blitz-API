from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from blitz_api.resources import UserPersonalDataResource


@shared_task
def alert_users_of_inactivity():
    alerted_users = []

    for user in get_user_model().objects.filter(anonymisation_date=None):
        
        inactivity_alert_period = timezone.timedelta(
            days=settings.LOCAL_SETTINGS['INACTIVITY_SETTINGS']['DAYS_BEFORE_ALERT']
        )

        last_seen = user.last_seen()
               
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

    for user in get_user_model().objects.filter(anonymisation_date=None):
        
        inactivity_disable_period = timezone.timedelta(
            days=settings.LOCAL_SETTINGS['INACTIVITY_SETTINGS']['DAYS_BEFORE_DISABLE']
        )

        last_seen = user.last_seen()
        
        # If user has been inactive for longer than the disable period, disable account
        if timezone.now() - last_seen > inactivity_disable_period:
            disabled_users.append(user.email)
            user.anonymise_and_disable_account()
            
    return disabled_users


@shared_task
def export_personal_data_of_users(author_id, user_id):
    queryset = get_user_model().objects.filter(id=user_id)

    dataset = UserPersonalDataResource().export(queryset)

    date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
        .strftime("%Y%m%d-%H%M%S")
    filename = f'export-personal-data-user-{user_id}-{date_file}.xls'

    new_export = ExportMedia.objects.create(
        name=filename,
        type=ExportMedia.EXPORT_PERSONAL_DATA,
        author_id=author_id
    )
    content = ContentFile(dataset.xls)
    new_export.file.save(filename, content)
    
    new_export.send_confirmation_email()
    
    return f"Exported personal data for user {user.email}"