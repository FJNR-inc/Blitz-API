import rest_framework
from rest_framework import viewsets, status, exceptions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from blitz_api.exceptions import MailServiceError
from blitz_api.services import send_mail

from .models import Workplace, Picture, Period, TimeSlot, Reservation

from . import serializers, permissions

User = get_user_model()


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

    def get_queryset(self):
        """
        This viewset should return active periods except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Period.objects.all()
        return Period.objects.filter(is_active=True)


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
    permission_classes = (permissions.IsAdminOrReadOnly,)
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

    def filter_queryset(self, queryset):
        """
        This viewset should return active timeslots except if
        the currently authenticated user is an admin (is_staff).
        """
        queryset = super(TimeSlotViewSet, self).filter_queryset(queryset)
        if self.request.user.is_staff:
            return queryset
        return queryset.filter(period__is_active=True)

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        instance = self.get_object()
        try:
            if (instance.users.exists() and
                    (validated_data.get('start_time') or
                     validated_data.get('end_time'))):
                with transaction.atomic():
                    new_instance = serializer.save()
                    context = {
                        "custom_message": validated_data.get('custom_message'),
                    }
                    reservation_cancel = Reservation.objects.filter(
                        timeslot=instance
                    )
                    affected_users_id = reservation_cancel.values_list('user')
                    affected_users = User.objects.filter(
                        id__in=affected_users_id,
                    )
                    # Failed emails are not sent back in the response yet
                    failed_emails = send_mail(
                        affected_users,
                        context,
                        "RESERVATION_CANCELLED",
                    )
                    return new_instance
        except MailServiceError as err:
            raise exceptions.APIException(err)
        return serializer.save()

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

        if instance.reservations.filter(is_active=True).exists():
            if not data.get('force_delete'):
                raise rest_framework.serializers.ValidationError({
                    "non_field_errors": [_(
                        "Trying to do a TimeSlot deletion that affects "
                        "users without providing `force_delete` field set "
                        "to True."
                    )]
                })

        reservation_cancel = instance.reservations.filter(
            is_active=True
        )
        affected_users_id = reservation_cancel.values_list('user')
        affected_users = User.objects.filter(
            id__in=affected_users_id,
        )

        with transaction.atomic():
            # The sequence is important here because the Queryset are
            # dynamically changing when doing update(). If the
            # `reservation_cancel` queryset objects are updated first, the
            # queryset will become empty since it was filtered using
            # "is_active=True". That would lead to an empty `affected_users`
            # queryset.
            affected_users.update(tickets=F('tickets') + 1)
            reservation_cancel.update(
                is_active=False,
                cancelation_reason='TD', # TimeSlot deleted
                cancelation_date=timezone.now(),
            )
            instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class ReservationViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given reservation.

    list:
    Return a list of all the existing reservations.

    create:
    Create a new reservation instance.
    """
    serializer_class = serializers.ReservationSerializer
    queryset = Reservation.objects.all()
    filter_fields = '__all__'
    ordering_fields = (
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'timeslot__start_time',
        'timeslot__end_time',
    )

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
