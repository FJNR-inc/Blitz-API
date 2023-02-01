import asyncio
from tomato.models import (
    Message,
    Attendance,
    Report, Tomato,
)
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
        if self.action in ['create', 'list', 'retrieve']:
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
            'community_tomato': t.aggregate(
                Sum('number_of_tomato'))['number_of_tomato__sum'],
        }
        return Response(response_data, status=status.HTTP_200_OK)
