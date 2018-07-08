from rest_framework import serializers, status
from rest_framework.validators import UniqueValidator

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils.translation import ugettext_lazy as _

from blitz_api.serializers import UserSerializer

from .models import Workplace, Picture, Period, TimeSlot, Reservation
from .fields import TimezoneField

User = get_user_model()


class WorkplaceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    timezone = TimezoneField(
        required=True,
        help_text=_("Timezone of the workplace."),
    )

    # June 7th 2018
    # The SlugRelatedField serializer can't get a field's attributes.
    # Ex: It can't get the "url" attribute of Imagefield Picture.picture.url
    # So here is a workaround: a SerializerMethodField is used to manually get
    # picture urls. This works but is not as clean as it could be.
    # Note: this is a read-only field so it isn't used for Workplace creation.
    pictures = serializers.SerializerMethodField()

    def get_pictures(self, obj):
        request = self.context['request']
        picture_urls = [
            picture.picture.url for picture in obj.pictures.all()
        ]
        return [request.build_absolute_uri(url) for url in picture_urls]

    class Meta:
        model = Workplace
        fields = '__all__'
        extra_kwargs = {
            'details': {'help_text': _("Description of the workplace.")},
            'name': {
                'help_text': _("Name of the workplace."),
                'validators': [
                    UniqueValidator(queryset=Workplace.objects.all())
                ],
            },
            'seats': {'help_text': _("Number of available seats.")},
        }


class PictureSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Picture
        fields = '__all__'
        extra_kwargs = {
            'workplace': {
                'help_text': _("Workplace represented by the picture.")
            },
            'name': {
                'help_text': _("Name of the picture."),
            },
            'picture': {
                'help_text': _("File to upload."),
            }
        }


class PeriodSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    def validate(self, attrs):
        """Prevents overlapping active periods and invalid start/end date"""
        # Forbid Period full updates if users have reserved timeslots
        action = self.context['view'].action
        if action == 'update' or action == 'partial_update':
            reservations = TimeSlot.objects.filter(
                period=self.instance
            ).exclude(users=None).count()
            if reservations:
                raise serializers.ValidationError(
                    _("The period contains timeslots with user reservations."),
                )
        # Get instance values of start_date, end_date and is_active if not
        # provided in request data (needed for validation).
        start = attrs.get(
            'start_date',
            getattr(self.instance, 'start_date', None)
        )
        end = attrs.get(
            'end_date',
            getattr(self.instance, 'end_date', None)
        )
        is_active = attrs.get(
            'is_active',
            getattr(self.instance, 'is_active', None)
        )

        if start >= end:
            raise serializers.ValidationError({
                'end_date': [_("End date must be later than start_date.")],
                'start_date': [_("Start date must be earlier than end_date.")],
            })

        # If creating/updating an active period, make sure that it does not
        # overlap with another active period
        if is_active:
            instance_id = getattr(self.instance, 'id', None)
            workplace = attrs.get(
                'workplace',
                getattr(self.instance, 'workplace', None)
            )
            # Get other active periods aasociated to the same workplace
            workplace_periods = Period.objects.filter(
                workplace=workplace,
                is_active=True,
            )
            # Exclude current period (for updates)
            workplace_periods = workplace_periods.exclude(id=instance_id)
            # Keep start_date & end_date for validation
            # This creates a list of tuple: [(start_date, end_date), ...]
            date_list = workplace_periods.values_list('start_date', 'end_date')

            for duration in date_list:
                if max(duration[0], start) < min(duration[1], end):
                    raise serializers.ValidationError(
                        _(
                            "An active period associated to the same "
                            "workplace overlaps with the provided start_date "
                            "and end_date."
                        ),
                    )

        return attrs

    class Meta:
        model = Period
        fields = '__all__'
        extra_kwargs = {
            'workplace': {
                'required': True,
                'help_text': _("Workplaces to which this period applies.")
            },
            'name': {
                'required': True,
                'help_text': _("Name of the period."),
            },
            'price': {
                'required': True,
                'help_text': _("Hourly rate applied to this period.")
            },
            'is_active': {
                'required': True,
                'help_text': _("Whether users can see this period or not.")
            },
            'start_date': {
                'required': True,
            },
            'end_date': {
                'required': True,
            },
        }


class TimeSlotSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    places_remaining = serializers.SerializerMethodField()
    # users = serializers.SerializerMethodField()
    workplace = WorkplaceSerializer(
        read_only=True,
        source='period.workplace',
    )
    force_update = serializers.BooleanField(
        required=False,
        write_only=True,
    )
    custom_message = serializers.CharField(
        required=False,
        write_only=True,
        max_length=1000,
    )

    def get_places_remaining(self, obj):
        if not obj.period.workplace:
            return 0
        seats = obj.period.workplace.seats
        reservations = obj.reservations.filter(is_active=True).count()
        return seats - reservations

    def validate(self, attrs):
        """Prevents overlapping timeslots and invalid start/end time"""
        # Get instance values of start_time and end_time if not
        # provided in request data (needed for validation).
        start = attrs.get(
            'start_time',
            getattr(self.instance, 'start_time', None)
        )
        end = attrs.get(
            'end_time',
            getattr(self.instance, 'end_time', None)
        )
        period = attrs.get(
            'period',
            getattr(self.instance, 'period', None)
        )
        # Will always be None if request method is not "update"
        instance_id = getattr(self.instance, 'id', None)

        # Make sure both DateTimes refer to the same day
        if start.date() != end.date():
            raise serializers.ValidationError({
                'end_time': [
                    _("End time must be the same day as start_time.")
                ],
                'start_time': [
                    _("Start time must be the same day as end_time.")
                ],
            })

        if start >= end:
            raise serializers.ValidationError({
                'end_time': [_("End time must be later than start_time.")],
                'start_time': [_("Start time must be earlier than end_time.")],
            })

        # Generate a list of tuples containing start/end time of existing
        # timeslots in the requested period.
        period_timeslots = TimeSlot.objects.filter(
            period=period
        )
        # Exclude current period (for updates)
        period_timeslots = period_timeslots.exclude(id=instance_id)
        time_list = period_timeslots.values_list('start_time', 'end_time')

        for duration in time_list:
            if max(duration[0], start) < min(duration[1], end):
                raise serializers.ValidationError({
                    'detail': _(
                        "An existing timeslot overlaps with the provided "
                        "start_time and end_time."
                    ),
                })

        return attrs

    @transaction.atomic()
    def update(self, instance, validated_data):
        """
        If it is an update operation, we check if users will be affected by
        the update. If yes, we make sure that the field "force_update" is
        provided in the request. If provided, cancel reservations and refund
        affected users tickets.
        """
        if instance.reservations.filter(is_active=True).exists():
            if (validated_data.get('start_time') or
                    validated_data.get('end_time')):
                if not validated_data.get('force_update'):
                    raise serializers.ValidationError({
                        "non_field_errors": [_(
                            "Trying to push an update that affects users "
                            "without providing `force_update` field."
                        )]
                    })
                reservation_cancel = instance.reservations.filter(
                    is_active=True
                )
                affected_users_id = reservation_cancel.values_list('user')
                affected_users = User.objects.filter(
                    id__in=affected_users_id,
                )

                # Order is important here because the Queryset are dynamically
                # changing when doing update(). If the `reservation_cancel`
                # queryset objects are updated first, the queryset will become
                # empty since it was filtered using "is_active=True". That
                # would lead to an empty `affected_users` queryset.
                affected_users.update(tickets=F('tickets') + 1)
                reservation_cancel.update(is_active=False)

        return super(TimeSlotSerializer, self).update(
            instance,
            validated_data,
        )

    def create(self, validated_data):
        """
        Uses period's price if no price is provided.
        """
        if 'price' not in validated_data:
            validated_data['price'] = validated_data['period'].price

        return super().create(validated_data)

    def to_representation(self, instance):
        if self.context['view'].action == 'retrieve':
            self.fields['users'] = UserSerializer(many=True)
        return super(TimeSlotSerializer, self).to_representation(instance)

    class Meta:
        model = TimeSlot
        exclude = ('name', )
        extra_kwargs = {
            'period': {
                'required': True,
                'help_text': _("Period to which this time slot applies.")
            },
            'name': {
                'required': True,
                'help_text': _("Name of the time slot."),
            },
            'price': {
                'help_text': _(
                    "Hourly rate applied to this time slot. Overrides period "
                    "price."
                )
            },
            'start_time': {
                'required': True,
            },
            'end_time': {
                'required': True,
            },
        }


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    def validate(self, attrs):
        """Prevents overlapping and no-workplace reservations."""
        validated_data = super(ReservationSerializer, self).validate(attrs)
        if 'timeslot' in attrs:
            if not attrs['timeslot'].period.workplace:
                raise serializers.ValidationError(
                    'No reservation are allowed for time slots without '
                    'workplace.'
                )

        if 'user' in validated_data or 'timeslot' in validated_data:
            # Generate a list of tuples containing start/end time of
            # existing reservations.
            start = validated_data['timeslot'].start_time
            end = validated_data['timeslot'].end_time
            active_reservations = Reservation.objects.filter(
                user=validated_data['user'],
                is_active=True,
            ).exclude(**validated_data).values_list(
                'timeslot__start_time',
                'timeslot__end_time'
            )

            for timeslots in active_reservations:
                if max(timeslots[0], start) < min(timeslots[1], end):
                    raise serializers.ValidationError(
                        'This reservation overlaps with another active '
                        'reservations for this user.'
                    )
        return attrs

    class Meta:
        model = Reservation
        fields = '__all__'
        extra_kwargs = {
            'is_active': {
                'required': True,
                'help_text': _("Whether the reservation is active or not."),
            },
        }
