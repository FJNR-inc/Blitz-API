import decimal
import json
from copy import copy
from datetime import datetime, timedelta

import requests

import pytz
import rest_framework
from blitz_api.exceptions import MailServiceError
from blitz_api.services import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import mail_admins
from django.core.mail import send_mail as django_send_mail
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from store.exceptions import PaymentAPIError
from store.services import refund_amount, PAYSAFE_EXCEPTION

from . import permissions, serializers
from .models import (Picture, Reservation, Retirement, WaitQueue,
                     WaitQueueNotification)
from .resources import (ReservationResource, RetirementResource,
                        WaitQueueNotificationResource, WaitQueueResource)
from .services import notify_reserved_retirement_seat

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

TAX = settings.LOCAL_SETTINGS['SELLING_TAX']


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
        if self.action == 'destroy':
            permission_classes = [
                permissions.IsOwner,
                IsAuthenticated,
            ]
        else:
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

        By canceling 'min_day_refund' days or more before the event, the user
         will be refunded 'refund_rate'% of the price paid.
        The user will receive an email confirming the refund or inviting the
         user to contact the support if his payment informations are no longer
         valid.
        If the user cancels less than 'min_day_refund' days before the event,
         no refund is made.

        Taxes are refunded proportionally to refund_rate.
        """

        instance = self.get_object()
        retirement = instance.retirement
        user = instance.user
        order_line = instance.order_line
        order = order_line.order

        respects_minimum_days = (
            (retirement.start_time - timezone.now()) >=
            timedelta(days=retirement.min_day_refund))

        if instance.is_active:
            if respects_minimum_days:
                try:
                    amount_no_tax = float(
                        retirement.price * retirement.refund_rate
                    )
                    amount_tax = TAX * amount_no_tax
                    total_amount = round(decimal.Decimal(
                        amount_no_tax + amount_tax
                    ), 2)
                    refund_response = refund_amount(
                        order.settlement_id,
                        int(total_amount)
                    )
                except PaymentAPIError as err:
                    if str(err) == PAYSAFE_EXCEPTION['3406']:
                        return Response(
                            {'non_field_errors': _("The order has not been "
                                                   "charged yet. Try again "
                                                   "later.")},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    return Response(
                        {'message': str(err)},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                instance.cancelation_action = 'R'
            else:
                instance.cancelation_action = 'N'

            instance.is_active = False
            instance.cancelation_reason = 'U'
            instance.cancelation_date = timezone.now()
            instance.save()

            retirement.reserved_seats += 1
            # Ask the external scheduler to start calling /notify if the
            # reserved_seats count == 1. Otherwise, the scheduler should
            # already be calling /notify at specified intervals.
            if retirement.reserved_seats == 1:
                scheduler_url = '{0}'.format(
                    settings.EXTERNAL_SCHEDULER['URL'],
                )

                # interval = retirement.notification_interval.total_seconds()

                data = {
                    "hour": timezone.now().hour,
                    "minute": (timezone.now().minute + 5) % 60,
                    # This is a relative URL
                    "url": '{0}{1}'.format(
                        reverse('retirement:waitqueuenotification-list'),
                        "/notify"
                    ),
                    # "initial_execution": True,
                    "description": "Retirement wait queue notification"
                }

                try:
                    r = requests.post(
                        scheduler_url,
                        auth=(
                            settings.EXTERNAL_SCHEDULER['USER'],
                            settings.EXTERNAL_SCHEDULER['PASSWORD'],
                        ),
                        json=data,
                    )
                    r.raise_for_status()
                except (requests.exceptions.HTTPError,
                        requests.exceptions.ConnectionError) as err:
                    mail_admins(
                        "Thèsez-vous: external scheduler error",
                        str(err.__traceback__)
                    )

            retirement.save()

            # Send an email if a refund has been issued
            if instance.cancelation_action == 'R':
                # Here, the 'details' key is used to provide details of the
                #  item to the email template.
                # As of now, only 'retirement' objects have the 'email_content'
                #  key that is used here. There is surely a better way to
                #  to handle that logic that will be more generic.
                items = [{
                    'price': retirement.price,
                    'name': "{0}: {1}".format(
                        _("Retirement"),
                        retirement.name
                    ),
                    'details':
                        retirement.email_content
                }]

                # Send order confirmation email
                merge_data = {
                    'DATETIME': timezone.localtime().strftime("%x %X"),
                    'ORDER_ID': order.id,
                    'CUSTOMER_NAME': user.first_name + " " + user.last_name,
                    'CUSTOMER_EMAIL': user.email,
                    'CUSTOMER_NUMBER': user.id,
                    'TYPE': "Remboursement",
                    'ITEM_LIST': items,
                    'COST': round(total_amount/100, 2),
                    'TAX': round(decimal.Decimal(amount_tax/100), 2),
                }

                plain_msg = render_to_string("refund.txt", merge_data)
                msg_html = render_to_string("refund.html", merge_data)

                django_send_mail(
                    "Confirmation de remboursement",
                    plain_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=msg_html,
                )
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        instance = self.get_object()
        retirement = instance.retirement
        wait_queue = retirement.wait_queue.all().order_by('created_at')
        for index, item in enumerate(wait_queue):
            if item == instance:
                wait_queue_pos = index
                break
        if wait_queue_pos < retirement.next_user_notified:
            retirement.next_user_notified -= 1
            retirement.save()
        return super(WaitQueueViewSet, self).destroy(request, *args, **kwargs)


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

    @action(detail=False, permission_classes=[])
    def notify(self, request):
        """
        That custom action allows an admin (or automated task) to notify
        users in wait queues of every retirement.
        For each retirement, there will be as many users notified as there are
        reserved seats.
        At the same time, this clears older notification logs. That part should
        be moved somewhere else.
        """
        # Checks if lastest notification is older than 24h
        # This is a hard-coded limitation to allow anonymous users to call
        # the function.
        time_limit = timezone.now() - timedelta(days=1)
        if WaitQueueNotification.objects.filter(created_at__gt=time_limit):
            response_data = {
                'detail': "Last notification was sent less than 24h ago."
            }
            return Response(response_data, status=status.HTTP_200_OK)

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
            response_data = {
                'detail': "No reserved seats.",
                'stop': True,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_204_NO_CONTENT)

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
