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
        'Numéro membre',  # django ID
        'Utilisateur.trice',
        'Université',
        'Domaine',
        'Niveau académique',
        'Prénom',
        'Nom',
        'Sexe',
        'Ville',
        'Numéro étudiant',
        'Code programme académique',
        'Valeur utilisée',
        'Élément associé',
        'Date d\'utilisation',
    ]
    writer.writerow(header)

    coupon = Coupon.objects.get(pk=coupon_id)

    for line in OrderLine.objects.filter(coupon=coupon):
        is_refunded = Refund.objects.filter(orderline=line).exists()
        if not is_refunded:
            line_array = [None] * len(header)
            user = line.order.user
            line_array[0] = user.id
            line_array[1] = user.email
            university = user.university
            line_array[2] = university.name if university else ''
            academic_field = user.academic_field
            line_array[3] = academic_field.name if academic_field else ''
            academic_level = user.academic_level
            line_array[4] = academic_level.name if academic_level else ''
            line_array[5] = user.first_name
            line_array[6] = user.last_name
            line_array[7] = user.gender
            line_array[8] = user.city
            line_array[9] = user.student_number
            line_array[10] = user.academic_program_code
            line_array[11] = line.coupon_real_value
            line_array[12] = line.content_object.name
            line_array[13] = (line.order.transaction_date.
                              astimezone(LOCAL_TIMEZONE).
                              strftime("%Y-%m-%d %H:%M:%S"))
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


@shared_task()
def export_orderlines_sales(admin_id, year, month):
    """
    Export the orderlines sales data to a csv file. Including refund
    """
    output_stream = io.StringIO()
    writer = csv.writer(output_stream)
    header = [
        'Numéro membre',  # django ID
        'Université',
        'Sexe',
        'Ville',
        'Age',
        'Date de transaction',
        'Fait par un admin',
        'Numéro de commande',
        'Type d\'élément',
        'Élément associé',
        'Quantité',
        'Coupon',
        'Valeur du coupon',
        'Prix total',
        'Metadata',
        'Nombre d\'options',
        'Montant remboursé',
        'Détails du remboursement',
        'Date de remboursement',
    ]
    writer.writerow(header)

    for line in OrderLine.objects.filter(
            order__transaction_date__year=year,
            order__transaction_date__month=month
    ):
        try:
            refund = Refund.objects.get(orderline=line)
        except Refund.DoesNotExist:
            refund = None
        order = line.order
        user = order.user
        coupon = line.coupon


        line_array = [None] * len(header)
        # User information
        line_array[0] = user.id
        line_array[1] = user.university
        line_array[2] = user.gender
        line_array[3] = user.city
        line_array[4] = user.birthdate

        # Order information
        line_array[5] = order.transaction_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        line_array[6] = order.is_made_by_admin
        line_array[7] = order.id

        # Orderline information
        line_array[8] = line.content_type
        line_array[9] = line.content_object
        line_array[10] = line.quantity

        # Coupon information
        line_array[11] = coupon
        line_array[12] = line.coupon_real_value if coupon else ''

        # Additional information
        line_array[13] = line.total_cost
        line_array[14] = line.metadata
        line_array[15] = line.options.count()

        # Refund information
        line_array[16] = refund.amount if refund else ''
        line_array[17] = refund.details if refund else ''
        line_array[18] = refund.refund_date.strftime('%Y-%m-%dT%H:%M:%SZ') if refund else ''

        writer.writerow(line_array)

    date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
        .strftime("%Y%m%d")
    filename = f'sales-refund-{date_file}.csv'
    new_export = ExportMedia.objects.create(
        name=filename,
        author_id=admin_id,
        type=ExportMedia.EXPORT_SALES_AND_REFUND
    )
    new_export.file.save(
        filename,
        ContentFile(output_stream.getvalue().encode()))
    new_export.send_confirmation_email()
