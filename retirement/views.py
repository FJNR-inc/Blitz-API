from copy import copy
from datetime import datetime, timedelta
import pytz

import rest_framework
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail as django_send_mail
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from blitz_api.exceptions import MailServiceError
from blitz_api.services import send_mail

from . import permissions, serializers
from .models import (Picture, Reservation, Retirement, WaitQueue,
                     WaitQueueNotification, )
from .resources import (ReservationResource, RetirementResource,
                        WaitQueueResource, WaitQueueNotificationResource)
from .services import notify_reserved_retirement_seat

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetirementViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given retirement.

    list:
    Return a list of all the existing retirements.

    create:
    Create a new retirement instance.
    """
    serializer_class = serializers.RetirementSerializer
    queryset = Retirement.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, )
    filter_fields = '__all__'
    ordering = ('name', 'start_time', 'end_time')

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = RetirementResource().export()
        response = HttpResponse(
            dataset.xls, content_type="application/vnd.ms-excel")
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Retirement-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response


class PictureViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given picture.

    list:
    Return a list of all the existing pictures.

    create:
    Create a new picture instance.
    """
    serializer_class = serializers.PictureSerializer
    queryset = Picture.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, )
    # It is impossible to filter Imagefield by default. This is why we declare
    # filter fields manually here.
    filter_fields = {
        'name',
        'retirement',
    }


class ReservationViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given reservation.

    list:
    Return a list of all the existing reservations.

    create:
    Create a new reservation instance.

    partial_update:
    Modify a reservation instance (ie: mark user as present).
    """
    serializer_class = serializers.ReservationSerializer
    queryset = Reservation.objects.all()
    filter_fields = '__all__'
    ordering_fields = (
        'is_active',
        'is_present',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
        'retirement__start_time',
        'retirement__end_time',
    )

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = ReservationResource().export()
        response = HttpResponse(
            dataset.xls, content_type="application/vnd.ms-excel")
        response['Content-Disposition'] = ''.join([
            'attachment; filename="RetirementReservation-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return the request user's reservations except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(user=self.request.user)

    def get_permissions(self):
        """
        Returns the list of permissions that this view requires.
        """
        # if self.action == 'destroy':
        #     permission_classes = [
        #         permissions.IsOwner,
        #         IsAuthenticated,
        #     ]
        # else:
        permission_classes = [
            permissions.IsAdminOrReadOnly,
            IsAuthenticated,
        ]
        return [permission() for permission in permission_classes]

    def update(self, request, *args, **kwargs):
        if self.action == "update":
            return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        return super(ReservationViewSet, self).update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        A user can cancel his reservation by "deleting" it. It will return an
        empty response as if it was deleted, but will instead modify specific
        fields to keep a track of events. Subsequent delete request won't do
        anything, but will return a success.
        User will be refund the retirement's "refund_rate" if we're at least
        "min_day_refund" days before the event.
        """
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # instance = self.get_object()
        # if instance.is_active:
        #     instance.is_active = False
        #     instance.cancelation_reason = 'U'
        #     instance.cancelation_date = timezone.now()
        #     instance.save()
        # return Response(status=status.HTTP_204_NO_CONTENT)


class WaitQueueViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given wait_queue element.

    list:
    Return a list of all owned wait_queue elements.

    create:
    Create a new wait_queue element instance.

    delete:
    Delete an owned wait_queue element instance (unsubscribe user from mailing
    list).
    """
    serializer_class = serializers.WaitQueueSerializer
    queryset = WaitQueue.objects.all()
    permission_classes = (IsAuthenticated, )
    filter_fields = '__all__'
    ordering_fields = (
        'created_at',
        'retirement__start_time',
        'retirement__end_time',
    )

    def get_queryset(self):
        """
        This viewset should return the request user's wait_queue except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return WaitQueue.objects.all()
        return WaitQueue.objects.filter(user=self.request.user)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = WaitQueueResource().export()
        response = HttpResponse(
            dataset.xls, content_type="application/vnd.ms-excel")
        response['Content-Disposition'] = ''.join([
            'attachment; filename="WaitQueue-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class WaitQueueNotificationViewSet(mixins.ListModelMixin,
                                   mixins.RetrieveModelMixin,
                                   viewsets.GenericViewSet, ):
    """
    list:
    Return a list of all owned notification.

    read:
    Return a single owned notification.
    """
    serializer_class = serializers.WaitQueueNotificationSerializer
    queryset = WaitQueueNotification.objects.all()
    permission_classes = (IsAdminUser, )
    filter_fields = '__all__'
    ordering_fields = (
        'created_at',
        'retirement__start_time',
        'retirement__end_time',
    )

    def get_queryset(self):
        """
        The queryset contains all objects since the view is restricted to
        admins.
        """
        return WaitQueueNotification.objects.all()

    @action(detail=False, permission_classes=[IsAdminUser])
    def notify(self, request):
        """
        That custom action allows an admin (or automated task) to notify
        users in wait queues of every retirement.
        For each retirement, there will be as many users notified as there are
        reserved seats.
        At the same time, this clears older notification logs. That part should
        be moved somewhere else.
        """
        response = Response(
            status=status.HTTP_204_NO_CONTENT,
        )

        # Remove older notifications
        remove_before = timezone.now() - timedelta(
            days=settings.LOCAL_SETTINGS[
                'RETIREMENT_NOTIFICATION_LIFETIME_DAYS'
            ]
        )
        WaitQueueNotification.objects.filter(
            created_at__lt=remove_before
        ).delete()

        # Get retirements that have reserved seats
        retirements = Retirement.objects.filter(reserved_seats__gt=0)

        for retirement in retirements:
            # Get the wait queue with elements ordered by ascending date
            wait_queue = retirement.wait_queue.all().order_by('created_at')
            # Get number of waiting users
            nb_waiting_users = wait_queue.count()
            # If all users have already been notified, free all reserved seats
            if retirement.next_user_notified >= nb_waiting_users:
                retirement.reserved_seats = 0
                retirement.next_user_notified = 0
            # Else notify a user for every reserved seat
            for seat in range(retirement.reserved_seats):
                if retirement.next_user_notified >= nb_waiting_users:
                    retirement.reserved_seats -= 1
                else:
                    user = wait_queue[retirement.next_user_notified].user
                    notify_reserved_retirement_seat(
                        user,
                        retirement,
                    )
                    retirement.next_user_notified += 1
                    WaitQueueNotification.objects.create(
                        user=user,
                        retirement=retirement,
                    )

            retirement.save()

        if Retirement.objects.filter(reserved_seats__gt=0).count() == 0:
            response.data = {
                'detail': "No reserved seats."
            }
            response.status_code = status.HTTP_200_OK

        return response

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = WaitQueueNotificationResource().export()
        response = HttpResponse(
            dataset.xls, content_type="application/vnd.ms-excel")
        response['Content-Disposition'] = ''.join([
            'attachment; filename="WaitQueueNotification-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response
