import json
from datetime import datetime, timedelta

import pytz
from django.core.files.base import ContentFile

from blitz_api.mixins import ExportMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail as django_send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import (
    mixins,
    status,
    viewsets,
)
from rest_framework import serializers as rest_framework_serializers
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response

from blitz_api.models import ExportMedia
from blitz_api.serializers import ExportMediaSerializer
from log_management.models import (
    Log,
    EmailLog,
)
from store.exceptions import PaymentAPIError
from store.models import OrderLineBaseProduct
from store.services import PAYSAFE_EXCEPTION

from . import (
    permissions,
    serializers,
)
from .models import (
    Picture,
    Reservation,
    Retreat,
    WaitQueue,
    RetreatInvitation,
    WaitQueuePlace,
    WaitQueuePlaceReserved,
    RetreatType,
    AutomaticEmail,
    AutomaticEmailLog,
    RetreatDate,
)
from .resources import (
    ReservationResource,
    RetreatResource,
    WaitQueueResource,
    RetreatReservationResource,
    OptionProductResource,
)
from .serializers import (
    RetreatTypeSerializer,
    AutomaticEmailSerializer,
    RetreatDateSerializer,
)
from .services import (
    send_retreat_reminder_email,
    send_post_retreat_email,
    send_automatic_email,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

TAX = settings.LOCAL_SETTINGS['SELLING_TAX']


class RetreatViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given retreat.

    list:
    Return a list of all the existing retreats.

    create:
    Create a new retreat instance.
    """
    serializer_class = serializers.RetreatSerializer
    queryset = Retreat.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filterset_fields = {
        'is_active': ['exact'],
        'hidden': ['exact'],
        'type__id': ['exact'],
        'start_time': ['exact', 'gte', 'lte'],
        'end_time': ['exact', 'gte', 'lte'],
    }
    ordering = [
        'name',
    ]

    export_resource = RetreatResource()

    def get_queryset(self):
        """
        This viewset should return active retreats except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Retreat.objects.all()
        return Retreat.objects.filter(is_active=True,
                                      hidden=False)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_active:
            instance.is_active = False
            instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=[IsAdminUser], methods=['post'])
    def activate(self, request, pk=None):
        """
        That custom action allows an admin to activate
        a retreat and to run all the automations related.
        """
        retreat = self.get_object()

        try:
            retreat.activate()
        except ValueError as error:
            return Response(
                {
                    'non_field_errors': [str(error)],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(retreat)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=[])
    def execute_automatic_email(self, request, pk=None):
        """
        That custom action allows an admin (or an automated task) to
        notify a users who will attend the retreat with an existing
        automated email pre-configured (AutomaticEmail).
        """
        retreat = self.get_object()
        try:
            email = AutomaticEmail.objects.get(request.GET.get('message'))
        except Exception:
            response_data = {
                'detail': "AutomaticEmail not found"
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        # Notify a user for every reserved seat
        emails = []
        for reservation in retreat.reservations.filter(is_active=True):
            if reservation.automatic_email_logs.filter(email=email):
                pass
            else:
                send_automatic_email(reservation.user, retreat, email)
                AutomaticEmailLog.objects.create(
                    reservation=reservation,
                    email=email
                )
                emails.append(reservation.user.email)

        response_data = {
            'stop': True,
            'emails': emails
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=[])
    def remind_users(self, request, pk=None):
        """
        That custom action allows an admin (or automated task) to notify
        users who will attend the retreat.
        """
        retreat = self.get_object()
        if not retreat.is_active:
            response_data = {
                'detail': "Retreat need to be activate to send emails."
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # This is a hard-coded limitation to allow anonymous users to call
        # the function.
        time_limit = retreat.start_time - timedelta(days=8)
        if timezone.now() < time_limit:
            response_data = {
                'detail': "Retreat takes place in more than 8 days."
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # Notify a user for every reserved seat
        emails = []
        for reservation in retreat.reservations.filter(
                is_active=True, pre_event_send=False):
            send_retreat_reminder_email(reservation.user, retreat)
            reservation.pre_event_send = True
            reservation.save()
            emails.append(reservation.user.email)

        response_data = {
            'stop': True,
            'emails': emails
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=[])
    def recap(self, request, pk=None):
        """
        That custom action allows an admin (or automated task) to notify
        users who has attended the retreat.
        """
        retreat = self.get_object()
        # This is a hard-coded limitation to allow anonymous users to call
        # the function.
        time_limit = retreat.end_time - timedelta(days=1)
        if timezone.now() < time_limit:
            response_data = {
                'detail': "Retreat ends in more than 1 day."
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # Notify a user for every reserved seat
        emails = []
        for reservation in retreat.reservations.filter(
                is_active=True,
                post_event_send=False):
            send_post_retreat_email(reservation.user, retreat)
            reservation.post_event_send = True
            reservation.save()
            emails.append(reservation.user.email)

        response_data = {
            'stop': True,
            'emails': emails
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=[IsAdminUser])
    def export_participation(self, request, pk=None):

        retreat: Retreat = self.get_object()
        # Order queryset by ascending id, thus by descending age too
        queryset = Reservation.objects.filter(retreat=retreat)
        # Build dataset using paginated queryset
        dataset = RetreatReservationResource().export(queryset)

        date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
            .strftime("%Y%m%d-%H%M%S")
        filename = f'export-participation-{retreat.name}{date_file}.xls'

        new_exprt = ExportMedia.objects.create()
        content = ContentFile(dataset.xls)
        new_exprt.file.save(filename, content)

        export_url = ExportMediaSerializer(
            new_exprt,
            context={'request': request}
        ).data.get('file')

        response = Response(
            status=status.HTTP_200_OK,
            data={
                'file_url': export_url
            }
        )

        return response

    @action(detail=True, permission_classes=[IsAdminUser])
    def export_options(self, request, pk=None):

        retreat: Retreat = self.get_object()
        # Order queryset by ascending id, thus by descending age too
        queryset = OrderLineBaseProduct.objects.filter(
            order_line__object_id=retreat.id,
            order_line__content_type__model='retreat')
        # Build dataset using paginated queryset
        dataset = OptionProductResource().export(queryset)

        date_file = LOCAL_TIMEZONE.localize(datetime.now()) \
            .strftime("%Y%m%d-%H%M%S")
        filename = f'export-option-{retreat.name}-{date_file}.xls'

        new_exprt = ExportMedia.objects.create()
        content = ContentFile(dataset.xls)
        new_exprt.file.save(filename, content)

        export_url = ExportMediaSerializer(
            new_exprt,
            context={'request': request}
        ).data.get('file')

        response = Response(
            status=status.HTTP_200_OK,
            data={
                'file_url': export_url
            }
        )

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
    filterset_fields = {
        'name',
        'retreat',
    }


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
    filterset_fields = [
        'user',
        'retreat',
        'is_active',
        'retreat__type__is_virtual'
    ]
    ordering_fields = (
        'is_active',
        'is_present',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
    )

    export_resource = ReservationResource()

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
        if self.action == 'destroy' or self.action == 'partial_update':
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
        User will be refund the retreat's "refund_rate" if we're at least
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
        retreat = instance.retreat
        user = instance.user
        reservation_active = instance.is_active
        order_line = instance.order_line
        data = request.data
        force_refund = False

        if self.request.user.is_staff:
            force_refund = data.get('force_refund', False)

        if order_line:
            order = order_line.order
            refundable = instance.refundable
        else:
            order = None
            refundable = False

        respects_minimum_days = (
                (retreat.start_time - timezone.now()) >=
                timedelta(days=retreat.min_day_refund))

        # In order to process a refund we need to be in one of those
        # two cases:
        #
        #  1 - We respect the date limit to be refund and the retreat is
        #  refundable
        #
        #  2 - An admin want to force a refund and the user paid for
        #  his reservation

        process_refund = (respects_minimum_days and refundable) or\
                         (force_refund and order_line)

        with transaction.atomic():
            # No need to check for previous refunds because a refunded
            # reservation == canceled reservation, thus not active.
            if reservation_active:
                if order_line and order_line.quantity > 1:
                    raise rest_framework_serializers.ValidationError({
                        'non_field_errors': [_(
                            "The order containing this reservation has a "
                            "quantity bigger than 1. Please contact the "
                            "support team."
                        )]
                    })
                if process_refund:
                    try:
                        refund = instance.make_refund("Reservation canceled")
                    except PaymentAPIError as err:
                        if str(err) == PAYSAFE_EXCEPTION['3406']:
                            raise rest_framework_serializers.ValidationError({
                                'non_field_errors': [_(
                                    "The order has not been charged yet. Try "
                                    "again later."
                                )],
                                'detail': err.detail
                            })
                        raise rest_framework_serializers.ValidationError(
                            {
                                'message': str(err),
                                'non_field_errors': [_(
                                    "An error occured with the payment system."
                                    " Please try again later."
                                )],
                                'detail': err.detail
                            }
                        )
                    instance.cancelation_action = 'R'
                else:
                    instance.cancelation_action = 'N'

                instance.is_active = False

                if self.request.user.id != user.id:
                    instance.cancelation_reason = 'A'
                else:
                    instance.cancelation_reason = 'U'

                instance.cancelation_date = timezone.now()
                instance.save()

                free_seats = retreat.places_remaining
                if retreat.reserved_seats or free_seats == 1:
                    retreat.add_wait_queue_place(user)

                retreat.save()

        # Send an email if a refund has been issued
        if reservation_active and instance.cancelation_action == 'R':
            self.send_refund_confirmation_email(
                amount=round(refund.amount - refund.amount * TAX, 2),
                retreat=retreat,
                order=order,
                user=user,
                total_amount=refund.amount,
                amount_tax=round(refund.amount * TAX, 2),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def send_refund_confirmation_email(self, amount, retreat, order, user,
                                       total_amount, amount_tax):
        # Here the price takes the applied coupon into account, if
        # applicable.
        old_retreat = {
            'price': (amount * retreat.refund_rate) / 100,
            'name': "{0}: {1}".format(
                _("Retreat"),
                retreat.name
            )
        }

        # Send order confirmation email
        merge_data = {
            'DATETIME': timezone.localtime().strftime("%x %X"),
            'ORDER_ID': order.id,
            'CUSTOMER_NAME': user.first_name + " " + user.last_name,
            'CUSTOMER_EMAIL': user.email,
            'CUSTOMER_NUMBER': user.id,
            'TYPE': "Remboursement",
            'OLD_RETREAT': old_retreat,
            'COST': total_amount,
            'TAX': amount_tax,
        }

        plain_msg = render_to_string("refund.txt", merge_data)
        msg_html = render_to_string("refund.html", merge_data)

        try:
            response_send_mail = django_send_mail(
                "Confirmation de remboursement",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=msg_html,
            )

            EmailLog.add(user.email, 'refund', response_send_mail)
        except Exception as err:
            additional_data = {
                'title': "Confirmation de votre nouvelle adresse courriel",
                'default_from': settings.DEFAULT_FROM_EMAIL,
                'user_email': user.email,
                'merge_data': merge_data,
                'template': 'notify_user_of_change_email'
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise


class WaitQueueViewSet(ExportMixin, viewsets.ModelViewSet):
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
    permission_classes = (IsAuthenticated,)
    filterset_fields = '__all__'
    ordering_fields = (
        'created_at',
        'retreat__start_time',
        'retreat__end_time',
    )

    export_resource = WaitQueueResource()

    def get_queryset(self):
        """
        This viewset should return the request user's wait_queue except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return WaitQueue.objects.all()
        return WaitQueue.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        wait_queue_object: WaitQueue = self.get_object()
        retreat = wait_queue_object.retreat

        WaitQueuePlaceReserved.objects.filter(
            user=wait_queue_object.user,
            wait_queue_place__retreat=retreat
        ).delete()

        return super(WaitQueueViewSet, self).destroy(request, *args, **kwargs)


class RetreatInvitationViewSet(viewsets.ModelViewSet):

    serializer_class = serializers.RetreatInvitationSerializer
    queryset = RetreatInvitation.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filter_fields = '__all__'


class WaitQueuePlaceViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.WaitQueuePlaceSerializer
    queryset = WaitQueuePlace.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)

    @action(detail=True, permission_classes=[])
    def notify(self, request, pk=None):

        time_limit = timezone.now() - timedelta(hours=23, minutes=55)

        wait_queue_place: WaitQueuePlace = self.get_object()

        if not wait_queue_place.wait_queue_places_reserved.filter(
                create__gt=time_limit):
            detail, stop = wait_queue_place.notify()
            response_data = {
                'detail': detail,
                'wait_queue_place': wait_queue_place.id,
                'stop': stop,
            }
            if stop:
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(response_data, status=status.HTTP_202_ACCEPTED)
        else:
            response_data = {
                'wait_queue_place': wait_queue_place.id,
                'detail': "Last notification was sent less than 24h ago."
            }
            return Response(
                response_data,
                status=status.HTTP_429_TOO_MANY_REQUESTS)


class WaitQueuePlaceReservedViewSet(mixins.ListModelMixin,
                                    mixins.RetrieveModelMixin,
                                    viewsets.GenericViewSet, ):

    serializer_class = serializers.WaitQueuePlaceReservedSerializer
    queryset = WaitQueuePlaceReserved.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, IsAuthenticated)
    filterset_fields = '__all__'

    def get_queryset(self):

        if self.request.user.is_staff:
            return WaitQueuePlaceReserved.objects.all()
        return WaitQueuePlaceReserved.objects.filter(user=self.request.user)


class RetreatDateViewSet(viewsets.ModelViewSet):
    serializer_class = RetreatDateSerializer
    queryset = RetreatDate.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = '__all__'


class RetreatTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RetreatTypeSerializer
    queryset = RetreatType.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = ['is_virtual']


class AutomaticEmailViewSet(viewsets.ModelViewSet):
    serializer_class = AutomaticEmailSerializer
    queryset = AutomaticEmail.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = '__all__'
