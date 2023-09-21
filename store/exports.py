import csv
import io
import pytz

from celery import shared_task
from datetime import datetime

from django.core.files.base import ContentFile
from django.conf import settings

from blitz_api.models import ExportMedia
from store.models import (
    Coupon,
    OrderLine,
    Refund,
)

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@shared_task()
def generate_coupon_usage(admin_id, coupon_id):
    """
    For given coupon, generate a csv file for usage data.
    :params admin_id: id of admin doing the request
    :params coupon_id: id of django coupon object
    """
    output_stream = io.StringIO()
    writer = csv.writer(output_stream)
    header = [
        'Utilisateur.trice', 'Université', 'Prénom', 'Nom',
        'Numéro étudiant', 'Code programme académique', 'Valeur utilisée',
        'Élément associé',
    ]
    writer.writerow(header)

    coupon = Coupon.objects.get(pk=coupon_id)

    for line in OrderLine.objects.filter(coupon=coupon):
        is_refunded = Refund.objects.filter(orderline=line).exists()
        if not is_refunded:
            line_array = [None] * len(header)
            user = line.order.user
            line_array[0] = user.email
            university = user.university
            line_array[1] = university.name if university else ''
            line_array[2] = user.first_name
            line_array[3] = user.last_name
            line_array[4] = user.student_number
            line_array[5] = user.academic_program_code
            line_array[6] = line.coupon_real_value
            line_array[7] = line.content_object.name
            writer.writerow(line_array)

    date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
        .strftime("%Y%m%d")
    filename = f'coupon-usage-{coupon.code}-{date_file}.csv'
    new_export = ExportMedia.objects.create(
        name=filename,
        author_id=admin_id,
        type=ExportMedia.EXPORT_COUPON_USAGE
    )
    new_export.file.save(
        filename,
        ContentFile(output_stream.getvalue().encode()))
    new_export.send_confirmation_email()
