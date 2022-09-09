import csv
import io

from celery import shared_task

from django.core.files.base import ContentFile
from django.db.models import QuerySet, Sum
from django.utils import timezone

from blitz_api.models import ExportMedia


def generate_retreat_sales(
        queryset: QuerySet
):

    output_stream = io.StringIO()
    writer = csv.writer(output_stream)

    header = [
        'name', 'date', 'hour', 'quantity'
    ]

    writer.writerow(header)

    for retreat in queryset:
        line_array = [None] * 4

        start_time = retreat.start_time
        start_time = start_time if start_time is not None else timezone.now()

        quantity = retreat.order_lines.aggregate(
            quantity=Sum('quantity')
        ).get('quantity')
        quantity = quantity if quantity is not None else 0

        line_array[0] = retreat.name
        line_array[1] = start_time.strftime('%Y-%m-%d')
        line_array[2] = start_time.strftime('%H:%M')
        line_array[3] = quantity

        writer.writerow(line_array)

    new_export = ExportMedia.objects.create(type=ExportMedia.EXPORT_RETREAT_SALES)
    new_export.file.save(
        f'export_retreats_sales.csv',
        ContentFile(output_stream.getvalue().encode()))

    return new_export


@shared_task()
def generate_retreat_room_distribution(
        admin_id,
        queryset: QuerySet
):
    """
    For given retreats, generate a csv file for room distribution
    :params admin_id: id of admin doing the request
    :params queryset: django queryset of retreat objects
    """

    for retreat in queryset:
        output_stream = io.StringIO()
        writer = csv.writer(output_stream)

        header = [
            'Nom', 'Prénom', 'email', 'Option de chambre', 'Préférence de genre',
            'Souhaite partager avec', 'Numéro de chambre'
        ]

        writer.writerow(header)
        participants_distribution_data = retreat.get_retreat_room_distribution()

        for p in participants_distribution_data:
            line_array = [None] * 7
            line_array[0] = p['last_name']
            line_array[1] = p['first_name']
            line_array[2] = p['email']
            line_array[3] = p['room_option']
            line_array[4] = p['gender_preference']
            line_array[5] = p['share_with']
            line_array[6] = p['room_number']

            writer.writerow(line_array)

        file_name = f'export_{retreat.name}_retreat_room_distribution.csv'
        new_export = ExportMedia.objects.create(
            name=file_name,
            author_id=admin_id,
            type=ExportMedia.EXPORT_RETREAT_ROOM_DISTRIBUTION
        )
        new_export.file.save(
            file_name,
            ContentFile(output_stream.getvalue().encode()))
        new_export.send_confirmation_email()
