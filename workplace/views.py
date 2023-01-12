import pytz

from copy import copy

import rest_framework
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail as django_send_mail
from django.db import transaction
from django.db.models import F, Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.utils import json

from blitz_api.mixins import ExportMixin
from log_management.models import Log, EmailLog

from .models import Workplace, Picture, Period, TimeSlot, Reservation
from .resources import (WorkplaceResource, PeriodResource, TimeSlotResource,
                        ReservationResource)
from . import serializers, permissions

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WorkplaceViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given workplace.

    list:
    Return a list of all the existing workplaces.

    create:
    Create a new workplace instance.
    """
    serializer_class = serializers.WorkplaceSerializer
    queryset = Workplace.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filterset_fields = '__all__'
    ordering = ('name',)

    export_resource = WorkplaceResource()


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
    permission_classes = (permissions.IsAdminOrReadOnly,)
    # It is impossible to filter Imagefield by default. This is why we declare
    # filter fields manually here.
    filterset_fields = {
        'name',
        'workplace',
    }


class PeriodViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given period.

    list:
    Return a list of all the existing periods.

    create:
    Create a new period instance.
    """
    serializer_class = serializers.PeriodSerializer
    queryset = Period.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filterset_fields = {
        'name': ['exact'],
        'workplace': ['exact'],
        'is_active': ['exact'],
        'start_date': ['exact', 'gte', 'lte'],
        'end_date': ['exact', 'gte', 'lte'],
    }
    ordering = ('name',)

    export_resource = PeriodResource()

    def get_queryset(self):
        """
        This viewset should return active periods except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            queryset = Period.objects.all()
        else:
            queryset = Period.objects.filter(is_active=True)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        An admin can soft-delete a Period instance. From an API user
        perspective, this is no different from a normal delete.
        The deletion will automatically soft-delete associated timeslots,
        cancel those timeslots' reservations and  refund used tickets to the
        registered users.
        """
        instance = self.get_object()

        data = request.data
        serializer = serializers.PeriodSerializer(data=data)
        serializer.is_valid()
        if 'force_delete' in serializer.errors:
            raise rest_framework.serializers.ValidationError({
                'force_delete': serializer.errors['force_delete']
            })
        if 'custom_message' in serializer.errors:
            raise rest_framework.serializers.ValidationError({
                'custom_message': serializer.errors['custom_message']
            })

        if instance.time_slots.filter(reservations__is_active=True).exists():
            if not data.get('force_delete'):
                raise rest_framework.serializers.ValidationError({
                    "non_field_errors": [_(
                        "Trying to do a Period deletion that affects "
                        "users without providing `force_delete` field set "
                        "to True."
                    )]
                })

        custom_message = data.get('custom_message')

        reservation_cancel = Reservation.objects.filter(
            timeslot__period=instance, is_active=True
        )
        affected_users = User.objects.filter(
            reservations__in=reservation_cancel
        )

        with transaction.atomic():
            reservations_cancel_copy = copy(reservation_cancel)

            # The sequence is important here because the Queryset are
            # dynamically changing when doing update(). If the
            # `reservation_cancel` queryset objects are updated first, the
            # queryset will become empty since it was filtered using
            # "is_active=True". That would lead to an empty `affected_users`
            # queryset.
            #
            # For-loop required to handle duplicates (if user has multiple
            # reservations that must be canceled).
            # user.update(tickets=F('tickets') + 1)
            for user in affected_users:
                User.objects.filter(
                    email=user.email
                ).update(tickets=F('tickets') + 1)  # Increment tickets
            reservation_cancel.update(
                is_active=False,
                cancelation_reason='TD',  # Period deleted
                cancelation_date=timezone.now(),
            )
            instance.delete()

            for reservation in reservations_cancel_copy:
                merge_data = {
                    'TIMESLOT_LIST': [reservation.timeslot],
                    'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
                    'CUSTOM_MESSAGE': custom_message,
                }
                plain_msg = render_to_string(
                    "cancelation.txt",
                    merge_data
                )
                msg_html = render_to_string(
                    "cancelation.html",
                    merge_data
                )

                try:
                    response_send_mail = django_send_mail(
                        "Annulation d'un bloc de rédaction",
                        plain_msg,
                        settings.DEFAULT_FROM_EMAIL,
                        [reservation.user.email],
                        html_message=msg_html,
                    )

                    EmailLog.add(
                        reservation.user.email, 'cancelation',
                        response_send_mail)
                except Exception as err:
                    additional_data = {
                        'title': "Annulation d'un bloc de rédaction",
                        'default_from': settings.DEFAULT_FROM_EMAIL,
                        'user_email': user.email,
                        'merge_data': merge_data,
                        'template': 'cancelation'
                    }
                    Log.error(
                        source='SENDING_BLUE_TEMPLATE',
                        message=err,
                        additional_data=json.dumps(additional_data)
                    )
                    raise

            instance.time_slots.all().delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TimeSlotViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given time slot.

    list:
    Return a list of all the existing time slots.

    create:
    Create a new time slot instance.
    """
    serializer_class = serializers.TimeSlotSerializer
    queryset = TimeSlot.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, )
    # We need to find a way to use '__all__' without excluding nested
    # attributes through FKs such as period__workplace. For now, we declare
    # each fields one by one.
    filterset_fields = {
        'period__workplace': ['exact'],
        'period__is_active': ['exact'],
        'period': ['exact'],
        'users': ['exact'],
        'name': ['exact'],
        'price': ['exact', 'gte', 'lte'],
        'start_time': ['exact', 'gte', 'lte'],
        'end_time': ['exact', 'gte', 'lte'],
    }

    export_resource = TimeSlotResource()

    @action(methods=['post'], detail=False, permission_classes=[IsAdminUser])
    def batch_create(self, request):
        """
        This custom action allows an admin to batch create timeslots.

        Parameters:
            name: name to be used for all timeslots
            start_time: datetime (isoformat).
            end_time: datetime (isoformat).
            period: period in which timeslots are created. The period defines
                the max boundary of the timeslot batch.
            weekdays: Days of the week for which the timeslots are created.
                Takes a list of integer from 0:Monday to 6:Sunday.

        NOTE:
            The date from the datetimes (start_time & end_time) are used as
            boundaries for the batch creation.
            The time from the datetimes (start_time & end_time) are used as
            start time & end time for the timeslots to be created.

        ie:
            {
                'name': "test",
                'start_time': '2019-11-25T08:00:00',
                'end_time': '2019-12-25T12:00:00',
                'period': validated_data['period'],
                'weekdays': [0,4]
            }
            That will create timeslots named "test", with start_time=08:00:00
            and end_time=12:00:00 for every Monday and Thursday between
            2019-11-25 and 2019-12-25 if those dates are within the period
            date range.

        Process will abort if a conflict arise.
        """
        serializer = serializers.BatchTimeSlotSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)

        serializer.save()

        # The following commented code grabs the newly created timeslots and
        #  returns them in the request.
        #
        # data = serializer.save()
        # data = serializers.TimeSlotSerializer(
        #     data,
        #     many=True,
        #     context={
        #         'request': request,
        #         'view': self
        #     },
        # ).data
        #
        # return Response(data, status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_201_CREATED)

    def filter_queryset(self, queryset):
        """
        This viewset should return active timeslots except if
        the currently authenticated user is an admin (is_staff).
        """
        queryset = super(TimeSlotViewSet, self).filter_queryset(queryset)
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(period__is_active=True)

    def destroy(self, request, *args, **kwargs):
        """
        An admin can soft-delete a TimeSlot instance. From an API user
        perspective, this is no different from a normal delete.
        The deletion will automatically cancel associated reservations and
        refund used tickets to the registered users.
        """
        instance = self.get_object()

        data = request.data
        serializer = serializers.TimeSlotSerializer(data=data)
        serializer.is_valid()
        if 'force_delete' in serializer.errors:
            raise rest_framework.serializers.ValidationError({
                'force_delete': serializer.errors['force_delete']
            })
        if 'custom_message' in serializer.errors:
            raise rest_framework.serializers.ValidationError({
                'custom_message': serializer.errors['custom_message']
            })

        if instance.reservations.filter(is_active=True).exists():
            if not data.get('force_delete'):
                raise rest_framework.serializers.ValidationError({
                    "non_field_errors": [_(
                        "Trying to do a TimeSlot deletion that affects "
                        "users without providing `force_delete` field set "
                        "to True."
                    )]
                })

        custom_message = data.get('custom_message')

        reservation_cancel = instance.reservations.filter(
            is_active=True
        )
        affected_users = User.objects.filter(
            reservations__in=reservation_cancel
        )

        with transaction.atomic():
            reservations_cancel_copy = copy(reservation_cancel)

            # The sequence is important here because the Queryset are
            # dynamically changing when doing update(). If the
            # `reservation_cancel` queryset objects are updated first, the
            # queryset will become empty since it was filtered using
            # "is_active=True". That would lead to an empty `affected_users`
            # queryset.
            #
            # For-loop required to handle duplicates (if user has multiple
            # reservations that must be canceled).
            # user.update(tickets=F('tickets') + 1)
            for user in affected_users:
                User.objects.filter(
                    email=user.email
                ).update(tickets=F('tickets') + 1)  # Increment tickets

            reservation_cancel.update(
                is_active=False,
                cancelation_reason='TD',  # TimeSlot deleted
                cancelation_date=timezone.now(),
            )
            instance.delete()

            for reservation in reservations_cancel_copy:
                merge_data = {
                    'TIMESLOT_LIST': [instance],
                    'SUPPORT_EMAIL': settings.SUPPORT_EMAIL,
                    'CUSTOM_MESSAGE': custom_message,
                }
                plain_msg = render_to_string(
                    "cancelation.txt",
                    merge_data
                )
                msg_html = render_to_string(
                    "cancelation.html",
                    merge_data
                )
                try:
                    response_send_mail = django_send_mail(
                        "Annulation d'un bloc de rédaction",
                        plain_msg,
                        settings.DEFAULT_FROM_EMAIL,
                        [reservation.user.email],
                        html_message=msg_html,
                    )

                    EmailLog.add(
                        reservation.user.email,
                        'cancelation', response_send_mail)
                except Exception as err:
                    additional_data = {
                        'title': "Annulation d'un bloc de rédaction",
                        'default_from': settings.DEFAULT_FROM_EMAIL,
                        'user_email': reservation.user.email,
                        'merge_data': merge_data,
                        'template': 'cancelation'
                    }
                    Log.error(
                        source='SENDING_BLUE_TEMPLATE',
                        message=err,
                        additional_data=json.dumps(additional_data)
                    )
                    raise

        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationViewSet(ExportMixin, viewsets.ModelViewSet):
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

    filterset_fields = {
        'user': ['exact'],
        'timeslot': ['exact'],
        'is_active': ['exact'],
        'timeslot__start_time': ['exact', 'gte', 'lte'],
        'timeslot__end_time': ['exact', 'gte', 'lte'],
    }

    ordering_fields = (
        'is_active',
        'is_present',
        'cancelation_date',
        'cancelation_reason',
        'timeslot__start_time',
        'timeslot__end_time',
        'user__first_name',
        'user__last_name',
    )

    export_resource = ReservationResource()

    def get_queryset(self):
        """
        This viewset should return the request user's reservations except if
        the currently authenticated user is an admin (is_staff).
        """
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(
            Q(user=user) |
            Q(timeslot__period__workplace__volunteers=user, is_active=True)
        )

    def get_permissions(self):
        """
        Returns the list of permissions that this view requires.
        """
        if self.action == 'destroy':
            permission_classes = [
                permissions.IsOwner,
                IsAuthenticated,
            ]
        elif self.action == 'partial_update':
            permission_classes = [
                permissions.IsVolunteerOrUpdateReadOnly,
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
        An admin can also delete a reservation, but will have the choice to
        give back the reservation ticket to the user
        """
        instance = self.get_object()
        user = instance.user
        if instance.is_active:
            instance.is_active = False
            instance.cancelation_date = timezone.now()
            if self.request.user.id != user.id:
                instance.cancelation_reason = \
                    Reservation.CANCELATION_REASON_ADMIN_CANCELLED
            else:
                instance.cancelation_reason = \
                    Reservation.CANCELATION_REASON_USER_CANCELLED
            instance.save()
            if self.request.user.is_staff:
                ticket_return = request.data.get('ticket_return', False)
                if ticket_return:
                    # user.tickets can be None
                    user.tickets = 1 + user.tickets if user.tickets else 1
                    user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
