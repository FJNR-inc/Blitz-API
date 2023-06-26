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
    CouponUser,
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
        'user_email', 'university', 'user_firstname', 'user_lastname',
        'student_number', 'academic_program_code', 'uses',
    ]
    writer.writerow(header)

    coupon = Coupon.objects.get(pk=coupon_id)
    coupon_users = CouponUser.objects.filter(coupon=coupon)

    for usage in coupon_users:
        if usage.uses > 0:
            line_array = [None] * len(header)
            line_array[0] = usage.user.email
            university = usage.user.university
            line_array[1] = university.name if university else ''
            line_array[2] = usage.user.first_name
            line_array[3] = usage.user.last_name
            line_array[4] = usage.user.student_number
            line_array[5] = usage.user.academic_program_code
            line_array[6] = usage.uses

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
