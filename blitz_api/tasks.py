from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from blitz_api.resources import UserPersonalDataResource


@shared_task
def alert_users_of_inactivity():
    alerted_users = []

    for user in get_user_model().objects.filter(is_active=True):
        
        inactivity_alert_period = timezone.timedelta(
            days=5*365-30 # Approximately 59 months
        )

        # If user has never logged in, use date of account creation
        # Since we did not log last_login date before end of december 2025, set a minimum 2 years delay to all users before inactivity alerts
        min_date = max(
            timezone.datetime(2022, 12, 31, tzinfo=timezone.utc),
            user.date_joined
        )
        last_seen = user.last_login or min_date
               
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

    for user in get_user_model().objects.filter(is_active=True):
        
        inactivity_disable_period = timezone.timedelta(
            days=5*365 # Approximately 5 years
        )
        
        # If user has never logged in, use date of account creation
        # Since we did not log last_login date before end of december 2025, set a minimum 2 years delay to all users before disabling accounts
        min_date = max(
            timezone.datetime(2022, 12, 31, tzinfo=timezone.utc),
            user.date_joined
        )
        last_seen = user.last_login or min_date
        
        # If user has been inactive for longer than the disable period, disable account
        if timezone.now() - last_seen > inactivity_disable_period:
            disabled_users.append(user.email)
            user.anonymise_and_disable_account()
            
    return disabled_users


@shared_task
def export_personal_data_of_users(author_id, user_id):
    queryset = setting.AUTH_USER_MODEL.objects.filter(id=user_id)

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