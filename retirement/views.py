from datetime import datetime, timedelta
import locale
import pytz
from dateutil.rrule import rrule, DAILY
from django.core.files.base import ContentFile
from django.db.models import (
    Max,
    Min,
)
from django_filters import (
    FilterSet,
    IsoDateTimeFilter,
    NumberFilter,
    BooleanFilter,
)

from blitz_api.mixins import ExportMixin
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import (
    mixins,
    status,
    viewsets,
)
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.response import Response

from blitz_api.models import ExportMedia
from blitz_api.serializers import ExportMediaSerializer

from store.models import OrderLineBaseProduct

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
    RetreatUsageLog,
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
    BatchRetreatSerializer,
    RetreatUsageLogSerializer,
    BatchActivateRetreatSerializer,
)
from .services import (
    send_retreat_reminder_email,
    send_post_retreat_email,
    send_automatic_email,
)
from .exports import (
    generate_retreat_participation,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

TAX = settings.LOCAL_SETTINGS['SELLING_TAX']


class RetreatFilter(FilterSet):
    finish_after = IsoDateTimeFilter(
        field_name='max_end_date',
        lookup_expr='gte',
    )
    start_after = IsoDateTimeFilter(
        field_name='min_start_date',
        lookup_expr='gte',
    )
    start_before = IsoDateTimeFilter(
        field_name='min_start_date',
        lookup_expr='lte',
    )
    type__id = NumberFilter(
        field_name='type',
        lookup_expr='exact',
    )

    class Meta:
        model = Retreat
        fields = '__all__'


class RetreatReservationFilter(FilterSet):
    finish_after = IsoDateTimeFilter(
        field_name='max_end_date',
        lookup_expr='gte',
    )
    start_after = IsoDateTimeFilter(
        field_name='min_start_date',
        lookup_expr='gte',
    )
    finish_before = IsoDateTimeFilter(
        field_name='max_end_date',
        lookup_expr='lte',
    )
    start_before = IsoDateTimeFilter(
        field_name='min_start_date',
        lookup_expr='lte',
    )
    user = NumberFilter(
        field_name='user__id',
        lookup_expr='exact',
    )
    retreat = NumberFilter(
        field_name='retreat__id',
        lookup_expr='exact',
    )
    is_active = BooleanFilter(
        field_name='is_active'
    )
    retreat__type__is_virtual = BooleanFilter(
        field_name='retreat__type__is_virtual'
    )

    class Meta:
        model = Reservation
        fields = '__all__'


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
    permission_classes = (
        permissions.IsAdminOrReadOnly,
    )
    ordering = [
        'name',
    ]
    ordering_fields = (
        'display_start_time',
    )

    filter_class = RetreatFilter
    search_fields = ('name',)
    export_resource = RetreatResource()

    def get_queryset(self):
        """
        This viewset should return active retreats except if
        the currently authenticated user is an admin (is_staff).
        """

        if self.request.user.is_staff:
            queryset = Retreat.objects.all()
        else:
            queryset = Retreat.objects.filter(
                is_active=True,
                hidden=False
            )

        queryset = queryset.annotate(
            max_end_date=Max('retreat_dates__end_time'),
            min_start_date=Min('retreat_dates__start_time'),
        )

        # Filter by display_start_time lower than
        display_start_time_lte = self.request.query_params.get(
            'display_start_time_lte',
            None,
        )
        if display_start_time_lte:
            queryset = queryset.filter(
                display_start_time__lte=display_start_time_lte
            )

        # Filter by display_start_time greater than
        display_start_time_gte = self.request.query_params.get(
            'display_start_time_gte',
            None,
        )
        if display_start_time_gte:
            queryset = queryset.filter(
                display_start_time__gte=display_start_time_gte
            )
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deletion_message = request.data.get('deletion_message', None)
        force_refund = request.data.get('force_refund', False)
        if instance.total_reservations > 0 and not deletion_message:
            error = {
                'deletion_message': _("There is at least one participant to "
                                      "this retreat. Please provide a "
                                      "deletion message.")
            }
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        if instance.is_active:
            instance.custom_delete(deletion_message, force_refund)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @transaction.atomic()
    @action(methods=['post'], detail=False, permission_classes=[IsAdminUser])
    def batch_create(self, request):
        """
        This custom action allows an admin to batch create timeslots.
        :param request:
        :return:
        """
        serializer = BatchRetreatSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Create a list of start times for timeslots
        # Naive datetimes are used to avoid problems with DST (not handled by
        # rrule)
        retreat_start_dates = list(
            rrule(
                freq=DAILY,
                dtstart=validated_data.get(
                    'bulk_start_time'
                ).replace(tzinfo=None),
                until=validated_data.get('bulk_end_time').replace(tzinfo=None),
                byweekday=validated_data['weekdays'],
            )
        )

        # Create a list of end times for timeslots
        # Naive datetimes are used to avoid problems with DST (not handled by
        # rrule)
        retreat_end_dates = list(
            rrule(
                freq=DAILY,
                dtstart=validated_data.get('bulk_start_time').replace(
                    hour=validated_data.get('bulk_end_time').hour,
                    minute=validated_data.get('bulk_end_time').minute,
                    second=validated_data.get('bulk_end_time').second,
                    tzinfo=None,
                ),
                until=validated_data.get('bulk_end_time').replace(tzinfo=None),
                byweekday=validated_data['weekdays'],
            )
        )

        retreat_data_list = list()
        tz = pytz.timezone('America/Montreal')
        locale.setlocale(locale.LC_TIME, "fr_CA")
        validated_data.pop('bulk_start_time')
        validated_data.pop('bulk_end_time')
        validated_data.pop('weekdays')
        memberships = validated_data.pop('exclusive_memberships')

        for start, end in zip(retreat_start_dates, retreat_end_dates):
            if tz.localize(start).hour < 12:
                suffix = 'AM'
            else:
                suffix = 'PM'
            validated_data['name'] = tz.localize(start).strftime(
                "Bloc %d %b"
            ) + ' ' + suffix
            validated_data['display_start_time'] = tz.localize(start)
            new_retreat = Retreat.objects.create(**validated_data)
            new_retreat.exclusive_memberships.set(memberships)
            RetreatDate.objects.create(
                retreat=new_retreat,
                start_time=tz.localize(start),
                end_time=tz.localize(end),
            )
            new_retreat.activate()
            retreat_data_list.append(new_retreat)

        response = self.get_serializer(retreat_data_list, many=True).data

        return Response(
            status=status.HTTP_200_OK,
            data=response
        )

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

    @action(detail=False, permission_classes=[IsAdminUser], methods=['post'])
    def batch_activate(self, request):
        """
        That custom action allows an admin to activate
        a list of retreat and to run all the automations related.
        """
        serializer = BatchActivateRetreatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        retreat_ids = serializer.validated_data.get('retreats')

        # check if all the retreats exist
        list_of_retreat_not_existing = []
        for retreat_id in retreat_ids:
            try:
                retreat = Retreat.objects.get(pk=retreat_id)
            except Retreat.DoesNotExist:
                list_of_retreat_not_existing.append(retreat_id)

        if len(list_of_retreat_not_existing):
            return Response(
                {
                    'retreat_ids': [
                        _('These retreats does not exist: ') +
                        str(list_of_retreat_not_existing)
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Activation of all the retreats, we use an atomic transaction to
        # make the call idempotent in case of error
        with transaction.atomic():
            for retreat_id in retreat_ids:
                try:
                    retreat = Retreat.objects.get(pk=retreat_id)
                    retreat.activate()
                except ValueError as error:
                    return Response(
                        {
                            'retreat': retreat_id,
                            'non_field_errors': [str(error)],
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, permission_classes=[])
    def execute_automatic_email(self, request, pk=None):
        """
        That custom action allows an admin (or an automated task) to
        notify a users who will attend the retreat with an existing
        automated email pre-configured (AutomaticEmail).
        """
        try:
            retreat = Retreat.objects.get(pk=pk)
        except Exception:
            response_data = {
                'detail': "Retreat not found"
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

        try:
            email = AutomaticEmail.objects.get(
                id=int(request.GET.get('email'))
            )
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
        export = generate_retreat_participation(request.user.id, retreat.id)
        response = Response(
            status=status.HTTP_200_OK,
            data={
                'file_url': export.data.get('file')
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

        new_exprt = ExportMedia.objects.create(
            type=ExportMedia.EXPORT_RETREAT_OPTIONS,
        )
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

    filter_class = RetreatReservationFilter

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
            queryset = Reservation.objects.all()
        else:
            queryset = Reservation.objects.filter(user=self.request.user)

        return queryset.annotate(
            max_end_date=Max('retreat__retreat_dates__end_time'),
            min_start_date=Min('retreat__retreat_dates__start_time'),
        ).order_by('min_start_date')

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
        """

        instance = self.get_object()
        user = instance.user
        force_refund = False

        if self.request.user.is_staff:
            force_refund = request.data.get('force_refund', False)
        if self.request.user.id != user.id:
            cancel_reason = Reservation.CANCELATION_REASON_ADMIN_CANCELLED
        else:
            cancel_reason = Reservation.CANCELATION_REASON_USER_CANCELLED

        refund_data = instance.process_refund(cancel_reason, force_refund)
        if refund_data:
            Reservation.send_refund_confirmation_email(refund_data)

        return Response(status=status.HTTP_204_NO_CONTENT)


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
            queryset = WaitQueuePlaceReserved.objects.all()
        else:
            queryset = WaitQueuePlaceReserved.objects.filter(
                user=self.request.user,
            )

        # Filter by retreat
        retreat = self.request.query_params.get('retreat', None)
        if retreat:
            queryset = queryset.filter(
                wait_queue_place__retreat__id=retreat
            )

        return queryset


class RetreatDateViewSet(viewsets.ModelViewSet):
    serializer_class = RetreatDateSerializer
    queryset = RetreatDate.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = '__all__'


class RetreatTypeViewSet(viewsets.ModelViewSet):
    serializer_class = RetreatTypeSerializer
    queryset = RetreatType.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = [
        'is_virtual',
        'is_visible',
    ]
    search_fields = ('name',)

    def get_queryset(self):
        if self.request.user.is_staff:
            queryset = RetreatType.objects.all()
        else:
            queryset = RetreatType.objects.filter(
                is_visible=True,
            )

        return queryset


class AutomaticEmailViewSet(viewsets.ModelViewSet):
    serializer_class = AutomaticEmailSerializer
    queryset = AutomaticEmail.objects.all()
    permission_classes = [permissions.IsAdminOrReadOnly]
    filter_fields = '__all__'


class RetreatUsageLogViewSet(viewsets.ModelViewSet):
    serializer_class = RetreatUsageLogSerializer
    queryset = RetreatUsageLog.objects.all()
    permission_classes = [IsAuthenticated]
    filter_fields = '__all__'
