import csv
import io
import pytz

from celery import shared_task
from datetime import datetime

from django.core.files.base import ContentFile
from django.db.models import QuerySet, Sum
from django.utils import timezone
from django.conf import settings

from blitz_api.models import ExportMedia
from blitz_api.serializers import ExportMediaSerializer
from retirement.models import Retreat

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


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

    new_export = ExportMedia.objects.create(
        type=ExportMedia.EXPORT_RETREAT_SALES,
    )
    new_export.file.save(
        f'export_retreats_sales.csv',
        ContentFile(output_stream.getvalue().encode()))

    return new_export


@shared_task()
def generate_retreat_participation(
        admin_id,
        retreat_id
):
    """
    For given retreat, generate a csv file for user data.
    If the retreat has room option, it will indicate the room distribution
    and order users in consequence.
    :params admin_id: id of admin doing the request
    :params retreat_id: id of django retreat object
    """
    output_stream = io.StringIO()
    writer = csv.writer(output_stream)
    retreat = Retreat.objects.get(pk=retreat_id)
    room_export = retreat.has_room_option
    rooms_data = {}
    to_reorder_lines = []
    header = [
        'Nom', 'Prénom', 'Email', 'Statut', "Date d'inscription",
        'Restrictions personnelles', 'Ville', 'Téléphone', 'Genre',
    ]
    if room_export:
        room_header = [
            'Option de chambre', 'Préférence de genre',
            'Souhaite partager avec', 'Numéro de chambre'
        ]
        header += room_header
        rooms_data = retreat.get_retreat_room_distribution()

    writer.writerow(header)

    for reservation in retreat.reservations.filter(is_active=True):
        line_array = [None] * len(header)
        line_array[0] = reservation.user.last_name
        line_array[1] = reservation.user.first_name
        line_array[2] = reservation.user.email
        line_array[3] = reservation.user.membership.name
        line_array[4] = reservation.order_line.order.transaction_date
        line_array[5] = reservation.user.personnal_restrictions
        line_array[6] = reservation.user.city
        line_array[7] = reservation.user.phone
        line_array[8] = reservation.user.gender

        if room_export:
            user_id = reservation.user.id
            line_array[9] = rooms_data[user_id]['room_option']
            line_array[10] = rooms_data[user_id]['gender_preference']
            line_array[11] = rooms_data[user_id]['share_with']
            line_array[12] = rooms_data[user_id]['room_number']
            to_reorder_lines.append(line_array)
        else:
            writer.writerow(line_array)  # No ordering if no room
    if room_export:
        # We need to export in room order
        for ordered_data in sorted(to_reorder_lines, key=lambda x: x[13]):
            writer.writerow(ordered_data)

    date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
        .strftime("%Y%m%d-%H%M%S")
    filename = f'export-participation-{retreat.name}_{date_file}.csv'
    new_export = ExportMedia.objects.create(
        name=filename,
        author_id=admin_id,
        type=ExportMedia.EXPORT_RETREAT_PARTICIPATION
    )
    new_export.file.save(
        filename,
        ContentFile(output_stream.getvalue().encode()))
    new_export.send_confirmation_email()

    return ExportMediaSerializer(new_export)
