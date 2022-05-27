import csv
import io

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

    new_export = ExportMedia.objects.create()
    new_export.file.save(
        f'export_retreats_sales.csv',
        ContentFile(output_stream.getvalue().encode()))

    return new_export
