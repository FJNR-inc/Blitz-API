from copy import copy
from datetime import datetime
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
from rest_framework import exceptions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from blitz_api.exceptions import MailServiceError
from blitz_api.services import send_mail

from . import permissions, serializers
from .models import Picture, Reservation, Retirement
from .resources import ReservationResource, RetirementResource

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
