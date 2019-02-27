import pytz

from copy import copy

from datetime import datetime

from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY

import rest_framework
from rest_framework import viewsets, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail as django_send_mail
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from blitz_api.exceptions import MailServiceError
from blitz_api.services import send_mail, ExportPagination

from .models import Workplace, Picture, Period, TimeSlot, Reservation
from .resources import (WorkplaceResource, PeriodResource, TimeSlotResource,
                        ReservationResource)

from . import serializers, permissions

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WorkplaceViewSet(viewsets.ModelViewSet):
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
    filter_fields = '__all__'
    ordering = ('name',)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        # Use custom paginator (by page, min/max 1000 objects/page)
        self.pagination_class = ExportPagination
        # Order queryset by ascending id, thus by descending age too
        queryset = self.get_queryset().order_by('pk')
        # Paginate queryset using custom paginator
        page = self.paginate_queryset(queryset)
        # Build dataset using paginated queryset
        dataset = WorkplaceResource().export(page)
        # Build response object
        response = self.get_paginated_response(dataset.xls)
        # Add filename to response
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Workplace-',
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
    permission_classes = (permissions.IsAdminOrReadOnly,)
    # It is impossible to filter Imagefield by default. This is why we declare
    # filter fields manually here.
    filter_fields = {
        'name',
        'workplace',
    }


class PeriodViewSet(viewsets.ModelViewSet):
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
    filter_fields = '__all__'
    ordering = ('name',)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        # Use custom paginator (by page, min/max 1000 objects/page)
        self.pagination_class = ExportPagination
        # Order queryset by ascending id, thus by descending age too
        queryset = self.get_queryset().order_by('pk')
        # Paginate queryset using custom paginator
        page = self.paginate_queryset(queryset)
        # Build dataset using paginated queryset
        dataset = PeriodResource().export(page)
        # Build response object
        response = self.get_paginated_response(dataset.xls)
        # Add filename to response
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Period-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return active periods except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Period.objects.all()
        return Period.objects.filter(is_active=True)

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
                django_send_mail(
                    "Annulation d'un bloc de rédaction",
                    plain_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation.user.email],
                    html_message=msg_html,
                )

            instance.time_slots.all().delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class TimeSlotViewSet(viewsets.ModelViewSet):
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
    filter_fields = {
        'period__workplace': ['exact'],
        'period__is_active': ['exact'],
        'period': ['exact'],
        'users': ['exact'],
        'name': ['exact'],
        'price': ['exact', 'gte', 'lte'],
        'start_time': ['exact', 'gte', 'lte'],
        'end_time': ['exact', 'gte', 'lte'],
    }

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        # Use custom paginator (by page, min/max 1000 objects/page)
        self.pagination_class = ExportPagination
        # Order queryset by ascending id, thus by descending age too
        queryset = self.get_queryset().order_by('pk')
        # Paginate queryset using custom paginator
        page = self.paginate_queryset(queryset)
        # Build dataset using paginated queryset
        dataset = TimeSlotResource().export(page)
        # Build response object
        response = self.get_paginated_response(dataset.xls)
        # Add filename to response
        response['Content-Disposition'] = ''.join([
            'attachment; filename="TimeSlot-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    @action(methods=['post'], detail=False, permission_classes=[IsAdminUser])
    def batch_create(self, request):
        """
        This custom action allows an admin to batch create timeslots.

        Parameters:
            name: name to be used for all timeslots
            start_time: datetime (isoformat) at which the timeslot begins
            end_time: datetime (isoformat) at which the timeslot ends
            period: period in which timeslots are created. The period defines
                the boundary of the timeslot batch.
            weekdays: Days of the week for which the timeslots are created.
                Takes a list of integer from 0:Monday to 6:Sunday.

        ie:
            {
                'name': "test",
                'start_time': '2002-12-25T08:00:00',
                'end_time': '2002-12-25T12:00:00',
                'period': validated_data['period'],
                'weekdays': [0,4]
            }
            That will create timeslots named "test", with start_time=08:00:00
            and end_time=12:00:00 for every Monday and Thursday between
            period.start_date and period.end_date.

        Process will abort if a conflict arise.
        """
        serializer = serializers.BatchTimeSlotSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        period_start_date = validated_data['period'].start_date
        period_end_date = validated_data['period'].end_date

        timeslot_data = {
            'name': validated_data['name'],
            'start_time': validated_data['start_time'],
            'end_time': validated_data['end_time'],
            'period': validated_data['period'],
        }

        timeslot_data_list = list()

        timeslot_dates = list(
            rrule(
                freq=DAILY,
                dtstart=period_start_date,
                until=period_end_date,
                byweekday=validated_data['weekdays'],
            )
        )

        with transaction.atomic():
            for day in timeslot_dates:
                timeslot_data['start_time'] = day.replace(
                    hour=validated_data['start_time'].hour,
                    minute=validated_data['start_time'].minute,
                    second=validated_data['start_time'].second,
                    tzinfo=None,
                )
                timeslot_data['end_time'] = day.replace(
                    hour=validated_data['end_time'].hour,
                    minute=validated_data['end_time'].minute,
                    second=validated_data['end_time'].second,
                    tzinfo=None,
                )
                timeslot_data_list.append(TimeSlot(**timeslot_data))

            TimeSlot.objects.bulk_create(timeslot_data_list)

        return Response("success", status=status.HTTP_200_OK)

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
                django_send_mail(
                    "Annulation d'un bloc de rédaction",
                    plain_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation.user.email],
                    html_message=msg_html,
                )

        return Response(status=status.HTTP_204_NO_CONTENT)


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
        'timeslot__start_time',
        'timeslot__end_time',
    )

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        # Use custom paginator (by page, min/max 1000 objects/page)
        self.pagination_class = ExportPagination
        # Order queryset by ascending id, thus by descending age too
        queryset = self.get_queryset().order_by('pk')
        # Paginate queryset using custom paginator
        page = self.paginate_queryset(queryset)
        # Build dataset using paginated queryset
        dataset = ReservationResource().export(page)
        # Build response object
        response = self.get_paginated_response(dataset.xls)
        # Add filename to response
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Reservation-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

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
        """
        instance = self.get_object()
        if instance.is_active:
            instance.is_active = False
            instance.cancelation_reason = 'U'
            instance.cancelation_date = timezone.now()
            instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
