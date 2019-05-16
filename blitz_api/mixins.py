from datetime import datetime

import pytz
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from blitz_api import serializers
from blitz_api.models import ExportMedia
from blitz_api.resources import UserResource
from blitz_api.services import ExportPagination

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ExportMixin(object):

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        # Use custom paginator (by page, min/max 1000 objects/page)
        self.pagination_class = ExportPagination
        # Order queryset by ascending id, thus by descending age too
        queryset = self.get_queryset().order_by('pk')
        # Paginate queryset using custom paginator
        page = self.paginate_queryset(queryset)
        # Build dataset using paginated queryset
        dataset = UserResource().export(page)

        date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
            .strftime("%Y%m%d-%H%M%S")
        filename = f'{request.resolver_match.view_name}-{date_file}.xls'

        new_exprt = ExportMedia.objects.create()
        content = ContentFile(dataset.xls)
        new_exprt.file.save(filename, content)

        export_url = serializers.ExportMediaSerializer(
            new_exprt,
            context={'request': request}).data.get('file')

        response = Response(
            status=status.HTTP_200_OK,
            data={
                'count': queryset.count(),
                'limit': self.pagination_class.page_size,
                'file_url': export_url
            }
        )

        return response
