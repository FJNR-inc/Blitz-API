import pytz
import asyncio
from django.conf import settings
from django.utils.dateparse import parse_datetime
from tomato.models import (
    Message,
    Attendance,
    Report, Tomato,
)
from django.db.models.functions import TruncMonth, TruncDay
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import (
    status,
    viewsets,
)
from rest_framework.decorators import action
from tomato.serializers import (
    MessageSerializer,
    AttendanceSerializer,
    ReportSerializer,
    AttendanceDeleteKeySerializer, TomatoSerializer,
)
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
    AllowAny,
)
from django.views.generic.base import TemplateView
from asgiref.sync import sync_to_async
import json
from datetime import datetime, timedelta
from django.db.models import Count, Sum


class IndexView(TemplateView):
    template_name = "index.html"


async def last_messages(socket, *args, **kwargs):
    await socket.accept()
    last_update = None
    last_time_sent = timezone.now()
    while True:
        await asyncio.sleep(2)
        if last_update:
            queryset = await sync_to_async(list)(
                Message.objects.filter(
                    posted_at__gte=last_update,
                ).prefetch_related(
                    'user',
                ).annotate(
                    report_count=Count('reports'),
                ).filter(
                    report_count=0,
                ).order_by(
                    '-posted_at',
                )
            )
        else:
            queryset = await sync_to_async(list)(
                Message.objects.all().prefetch_related(
                    'user',
                ).annotate(
                    report_count=Count('reports'),
                ).filter(
                    report_count=0,
                ).order_by(
                    '-posted_at',
                )[:50]
            )

        last_update = timezone.now()
        data = []
        for item in queryset:
            data.append(
                {
                    'id': item.id,
                    'message': item.message,
                    'author': {
                        'id': item.user.id,
                        'first_name': item.user.first_name,
                        'last_name': item.user.last_name,
                    },
                    'posted_at': datetime.timestamp(item.posted_at),
                }
            )

        if len(data):
            last_time_sent = timezone.now()
            await socket.send_text(json.dumps(data))
        elif last_time_sent < timezone.now() - timedelta(minutes=1):
            last_time_sent = timezone.now()
            await socket.send_text('')


async def current_attendances(socket, *args, **kwargs):
    await socket.accept()
    last_time_sent = timezone.now()
    last_count = 0
    while True:
        await asyncio.sleep(2)
        now = timezone.now()
        date_limit = now - timedelta(minutes=10)
        queryset = await sync_to_async(list)(
            Attendance.objects.filter(updated_at__gte=date_limit)
        )
        count = len(queryset)

        localisations = []
        for item in queryset:
            localisations.append(
                {
                    'longitude': str(item.longitude),
                    'latitude': str(item.latitude),
                }
            )

        if count != last_count:
            last_count = count
            last_time_sent = timezone.now()
            await socket.send_text(json.dumps(localisations))
        elif last_time_sent < timezone.now() - timedelta(minutes=1):
            last_time_sent = timezone.now()
            await socket.send_text('')


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    queryset = Message.objects.all()
    ordering = ('posted_at',)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        elif self.action in ['create']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    queryset = Attendance.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'delete_key', 'update_key']:
            permission_classes = []
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]

    @action(detail=False, permission_classes=[], methods=['post'])
    def delete_key(self, request):
        serializer = AttendanceDeleteKeySerializer(
            data=self.request.data,
            context={
                'request': request,
            },
        )
        serializer.is_valid(raise_exception=True)

        try:
            attendance = Attendance.objects.get(
                key=serializer.validated_data.get('key'),
            )
            attendance.delete()

            return Response('', status=status.HTTP_204_NO_CONTENT)
        except Attendance.DoesNotExist:
            return Response(
                {
                    'key': [_(
                        'This key does not exist'
                    )]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=False, permission_classes=[], methods=['post'])
    def update_key(self, request):
        serializer = AttendanceDeleteKeySerializer(
            data=self.request.data,
            context={
                'request': request,
            },
        )
        serializer.is_valid(raise_exception=True)

        try:
            attendance = Attendance.objects.get(
                key=serializer.validated_data.get('key'),
            )
            attendance.save()

            return Response('', status=status.HTTP_200_OK)
        except Attendance.DoesNotExist:
            return Response(
                {
                    'key': [_(
                        'This key does not exist'
                    )]
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class ReportViewSet(viewsets.ModelViewSet):
    serializer_class = ReportSerializer
    queryset = Report.objects.all()

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Report.objects.all()
        else:
            queryset = Report.objects.filter(user=self.request.user)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            permission_classes = [
                IsAuthenticated,
            ]
        else:
            permission_classes = [
                IsAdminUser,
            ]
        return [permission() for permission in permission_classes]


class TomatoViewSet(viewsets.ModelViewSet):
    serializer_class = TomatoSerializer
    queryset = Tomato.objects.all()
    filter_fields = {
        'user': ['exact'],
        'source': ['exact'],
        'acquisition_date': ['gte', 'lte']
    }

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = Tomato.objects.all()
        else:
            queryset = Tomato.objects.filter(user=self.request.user)

        return queryset

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve', 'statistics']:
            permission_classes = [
                IsAuthenticated,
            ]
        elif self.action in ['community_tomatoes']:
            permission_classes = [
                AllowAny,
            ]
        else:
            permission_classes = [
                IsAdminUser,
            ]
        return [permission() for permission in permission_classes]

    @staticmethod
    def get_queryset_number_of_tomatoes(queryset):
        """
        Returns the number of tomatoes for a given queryset
        """
        nb_tomatoes = queryset.aggregate(
            Sum('number_of_tomato'))['number_of_tomato__sum']
        nb_tomatoes = nb_tomatoes if nb_tomatoes else 0
        return nb_tomatoes

    @action(detail=False, methods=["get"])
    def community_tomatoes(self, request):
        """
        Return the total tomatoes done by all users in the current month.
        Special action because call doesn't require to be authenticated
        """
        today = timezone.now()
        start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        t = Tomato.objects.filter(
            acquisition_date__gte=start, acquisition_date__lte=today)
        response_data = {
            'community_tomato': self.get_queryset_number_of_tomatoes(t),
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        start = parse_datetime(request.query_params.get('start_date', None))
        end = parse_datetime(request.query_params.get('end_date', None))

        if not start or not end or end < start:
            return Response(
                {
                    'dates': _('Please select a valid start and end dates'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "totals": self._get_total_data(
                    start_date=start,
                    end_date=end,
                ),
                "graph": self._get_graph_data(
                    start_date=start,
                    end_date=end,
                )
            },
            status=status.HTTP_200_OK,
        )

    def _get_total_data(self, start_date, end_date):
        all_queryset = Tomato.objects.filter(
            acquisition_date__lte=end_date,
            acquisition_date__gte=start_date,
        )
        user_queryset = all_queryset.filter(user=self.request.user)
        totals = {
            "global": self.get_queryset_number_of_tomatoes(all_queryset),
            "user": self.get_queryset_number_of_tomatoes(user_queryset)
        }

        return totals

    def _get_graph_data(self, start_date, end_date):
        interval_param = self._define_interval(start_date, end_date)

        self.timezone = self.request.META.get(
            'HTTP_REQUEST_TIMEZONE',
            'America/Montreal',
        )

        start_date = start_date.astimezone(pytz.timezone(self.timezone))
        end_date = end_date.astimezone(pytz.timezone(self.timezone))

        queryset = Tomato.objects.filter(user=self.request.user)

        if end_date:
            queryset = queryset.filter(acquisition_date__lte=end_date)
        if start_date:
            queryset = queryset.filter(acquisition_date__gte=start_date)

        queryset = queryset.annotate(
            interval=self._trunc_interval(interval_param),
        )

        labels = self._get_intervals(start_date, end_date, interval_param)

        response_data = {
            'labels': labels,
            'datasets': self._get_datasets(queryset, labels)
        }

        return response_data

    @staticmethod
    def _define_interval(start_date, end_date):
        """
        Return interval based on date span. diff_date being given in days and
        seconds, we translate it in full seconds to handle partial day.
        """
        diff_date = end_date - start_date
        seconds_in_day = 3600 * 24
        seconds = diff_date.seconds + (diff_date.days * seconds_in_day)

        if seconds <= 31 * seconds_in_day:
            return 'day'
        else:
            return 'month'

    def _trunc_interval(self, interval_param):
        trunc_function = TruncMonth

        if interval_param == 'day':
            trunc_function = TruncDay

        return trunc_function(
            'acquisition_date', tzinfo=pytz.timezone(self.timezone)
        )

    @staticmethod
    def _get_intervals(start, end, interval_param):
        labels = set()

        date = start.replace(hour=0, minute=0, second=0)

        if interval_param == 'day':
            while end >= date:
                labels.add(
                    date.strftime("%Y-%m-%dT%H:%M:%S")
                )
                date += timedelta(days=1)
        else:
            date = date.replace(day=1)
            end = end.replace(day=1, hour=0, minute=0, second=0)
            while end >= date:
                labels.add(
                    date.strftime("%Y-%m-%dT%H:%M:%S")
                )
                # Get first day of next month
                date += timedelta(days=32)
                date = date.replace(day=1)

        labels = list(labels)
        labels.sort()
        return labels

    def _get_datasets(self, queryset, labels):
        queryset_by_interval = queryset.values('interval').annotate(
            number_of_tomato=(Sum('number_of_tomato')),
        )
        data_set_types = ['number_of_tomato']

        data_sets = []
        for data_set_type in data_set_types:
            data_set = {
                'label': data_set_type,
                'data': self._get_data(
                    queryset_by_interval,
                    data_set_type,
                    labels,
                )
            }
            data_sets.append(data_set)

        return data_sets

    @staticmethod
    def _get_data(queryset, data_set_type, labels):
        results = list()

        non_covered_labels = labels.copy()
        for data in queryset:
            label = data['interval'].strftime('%Y-%m-%dT%H:%M:%S')
            results.append(
                {
                    'x': label,
                    'y': data.get(data_set_type),
                }
            )
            non_covered_labels.remove(label)

        # Adding missing datasets
        for label in non_covered_labels:
            results.append(
                {
                    'x': label,
                    'y': 0.0,
                }
            )

        results.sort(key=lambda d: parse_datetime(d['x']))

        return results
