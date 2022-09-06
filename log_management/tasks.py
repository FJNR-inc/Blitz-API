from celery import shared_task
import datetime
import io
import csv
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task()
def export_anonymous_chrono_data(admin_id, start_date=None, end_date=None):
    """
    Allow an admin to export chrono data between 2 dates.
    Data will be anonymized and sent by email to the admin as CSV.
    :params admin_id: id of admin doing the export
    :params start_date: date to filter the range
    :params end_date: date to filter the range
    return nothing but will send an email when export is ready
    """
    from log_management.models import ActionLog
    from blitz_api.models import ExportMedia

    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')

    anonymized_actions = ActionLog.anonymize_data(start_date, end_date)

    # Create a csv
    export_data = []
    title = [None] * 5
    title[0] = 'Export Chrono Data'
    export_data.append(title)

    headers = [None] * 5
    headers[0] = 'User'
    headers[1] = 'Source'
    headers[2] = 'Action'
    headers[3] = 'Additional data'
    headers[4] = 'Timestamp'
    export_data.append(headers)

    for action in anonymized_actions:
        line_array = [None] * 5
        line_array[0] = action['user']
        line_array[1] = action['source']
        line_array[2] = action['action']
        line_array[3] = action['additional_data']
        line_array[4] = action['created']
        export_data.append(line_array)

    # Save CSV
    output_stream = io.StringIO()
    writer = csv.writer(output_stream)
    writer.writerows(export_data)
    if start_date and end_date:
        date_from_str = start_date.strftime('%Y-%m-%d')
        date_to_str = end_date.strftime('%Y-%m-%d')
        file_name = f'export_chrono_data_from_{date_from_str}_to_{date_to_str}.csv'
    else:
        file_name = f'export_chrono_data_all_{datetime.datetime.now().strftime("%Y-%m-%d")}.csv'
    new_export = ExportMedia.objects.create(
        name=file_name,
        author_id=admin_id,
        type=ExportMedia.EXPORT_ANONYMOUS_CHRONO_DATA,
    )
    new_export.file.save(
        file_name,
        ContentFile(output_stream.getvalue().encode()),
    )
    new_export.send_confirmation_email()
