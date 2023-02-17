import json
from copy import copy

from datetime import datetime

from dateutil.parser import parse
from dateutil.rrule import rrule, DAILY

import pytz

from rest_framework import serializers, status
from rest_framework.reverse import reverse
from rest_framework.validators import UniqueValidator

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from blitz_api.serializers import UserSerializer
from blitz_api.services import (remove_translation_fields,
                                check_if_translated_field,
                                getMessageTranslate,)
from log_management.models import Log, EmailLog

from .models import Workplace, Picture, Period, TimeSlot, Reservation
from .fields import TimezoneField

User = get_user_model()


class WorkplaceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    timezone = TimezoneField(
        required=False,
        help_text=_("Timezone of the workplace."),
    )
    name = serializers.CharField(
        required=False,
        validators=[UniqueValidator(queryset=Workplace.objects.all())]
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Workplace.objects.all())]
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Workplace.objects.all())]
    )
    details = serializers.CharField(
        required=False,
    )
    country = serializers.CharField(
        required=False,
    )
    state_province = serializers.CharField(
        required=False,
    )
    city = serializers.CharField(
        required=False,
    )
    address_line1 = serializers.CharField(
        required=False,
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

    def validate(self, attr):
        err = {}
        if not check_if_translated_field('name', attr):
            err.update(getMessageTranslate('name', attr, True))
        if not check_if_translated_field('details', attr):
            err.update(getMessageTranslate('details', attr, True))
        if not check_if_translated_field('country', attr):
            err.update(getMessageTranslate('country', attr, True))
        if not check_if_translated_field('state_province', attr):
            err.update(getMessageTranslate('state_province', attr, True))
        if not check_if_translated_field('city', attr):
            err.update(getMessageTranslate('city', attr, True))
        if not check_if_translated_field('address_line1', attr):
            err.update(getMessageTranslate('address_line1', attr, True))
        if not check_if_translated_field('timezone', attr):
            err['timezone'] = _("This field is required.")
        if not check_if_translated_field('postal_code', attr):
            err['postal_code'] = _("This field is required.")
        if not check_if_translated_field('seats', attr):
            err['seats'] = _("This field is required.")
        if err:
            raise serializers.ValidationError(err)
        return super(WorkplaceSerializer, self).validate(attr)

    def to_representation(self, instance):
        data = super(WorkplaceSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = Workplace
        exclude = ('deleted',)
        extra_kwargs = {
            'details': {'help_text': _("Description of the workplace.")},
            'name': {
                'help_text': _("Name of the workplace."),
                'validators': [
                    UniqueValidator(queryset=Workplace.objects.all())
                ],
            },
            'seats': {
                'required': False,
                'help_text': _("Number of available seats.")
            },
            'postal_code': {
                'required': False,
            },
        }


class PictureSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    def to_representation(self, instance):
        data = super(PictureSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

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
    force_delete = serializers.BooleanField(
        required=False,
        write_only=True,
    )
    custom_message = serializers.CharField(
        required=False,
        write_only=True,
        max_length=1000,
    )
    total_reservations = serializers.ReadOnlyField()
    name = serializers.CharField(
        required=False,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        """Prevents overlapping active periods and invalid start/end date"""
        if not check_if_translated_field('name', attrs):
            raise serializers.ValidationError({
                'name': _("This field is required.")
            })
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

    def to_representation(self, instance):
        data = super(PeriodSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = Period
        exclude = ('deleted',)
        extra_kwargs = {
            'workplace': {
                'required': True,
                'help_text': _("Workplaces to which this period applies.")
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
    billing_price = serializers.ReadOnlyField()
    places_remaining = serializers.SerializerMethodField()
    nb_reservations_active = serializers.SerializerMethodField()
    nb_reservations_canceled = serializers.SerializerMethodField()
    is_reserved = serializers.SerializerMethodField()
    workplace = WorkplaceSerializer(
        read_only=True,
        source='period.workplace',
    )
    force_update = serializers.BooleanField(
        required=False,
        write_only=True,
    )
    force_delete = serializers.BooleanField(
        required=False,
        write_only=True,
    )
    custom_message = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        write_only=True,
        max_length=1000,
    )

    def get_is_reserved(self, timeslot: TimeSlot):
        user = self.context['request'].user

        return Reservation.objects.filter(
            is_active=True,
            user=user.pk,
            timeslot=timeslot,
        ).exists()

    def get_nb_reservations_active(self, obj):
        return Reservation.objects.filter(
            is_active=True,
            timeslot=obj,
        ).count()

    def get_nb_reservations_canceled(self, obj):
        return Reservation.objects.filter(
            is_active=False,
            timeslot=obj,
        ).count()

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

        # Make sure that force_update is provided for update operations
        action = self.context['view'].action
        if action in ['update', 'partial_update']:
            if self.instance.reservations.filter(is_active=True).exists():
                if not attrs.get('force_update'):
                    raise serializers.ValidationError({
                        "non_field_errors": [_(
                            "Trying to push an update that affects users "
                            "without providing `force_update` field."
                        )]
                    })
        attrs.pop('force_update', None)

        # Make sure that start_time & end_time are within the period's
        # start_date & end_date
        if start < period.start_date or start > period.end_date:
            raise serializers.ValidationError({
                'start_time': [_(
                    "Start time must be set within the period's start_date "
                    "and end_date."
                )],
            })
        if end < period.start_date or end > period.end_date:
            raise serializers.ValidationError({
                'end_time': [_(
                    "End time must be set within the period's start_date "
                    "and end_date."
                )],
            })

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
        # Exclude current timeslot (for updates)
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
                custom_message = validated_data.get('custom_message')
                reservation_cancel = instance.reservations.filter(
                    is_active=True
                )
                affected_users = User.objects.filter(
                    reservations__in=reservation_cancel
                )

                reservations_cancel_copy = copy(reservation_cancel)

                affected_users.update(tickets=F('tickets') + 1)
                reservation_cancel.update(
                    is_active=False,
                    cancelation_reason='TM',  # TimeSlot modified
                    cancelation_date=timezone.now(),
                )

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
                        response_send_mail = send_mail(
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
        data = super(TimeSlotSerializer, self).to_representation(instance)
        return remove_translation_fields(data)

    class Meta:
        model = TimeSlot
        exclude = ('deleted', 'users')
        extra_kwargs = {
            'period': {
                'required': True,
                'help_text': _("Period to which this time slot applies.")
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


class BatchTimeSlotSerializer(serializers.HyperlinkedModelSerializer):
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    period = serializers.HyperlinkedRelatedField(
        view_name='period-detail',
        queryset=Period.objects.all(),
    )
    weekdays = serializers.ListField(
        child=serializers.IntegerField(
            max_value=6,
            min_value=0
        )
    )

    def validate_weekdays(self, weekdays):
        """
        Check that no weekday is duplicated.
        """
        if len(weekdays) != len(set(weekdays)):
            raise serializers.ValidationError(_(
                "Duplicated weekdays are not authorized."
            ))
        return weekdays

    def validate(self, attrs):
        validated_data = super(BatchTimeSlotSerializer, self).validate(attrs)
        period = validated_data['period']
        period_start_date = period.start_date
        period_end_date = period.end_date
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        # Use workplace's timezone if possible. Otherwise use Montreal timezone
        if period.workplace and period.workplace.timezone:
            tz = pytz.timezone(period.workplace.timezone)
        else:
            tz = pytz.timezone('America/Montreal')

        # Convert provided date and time to timezone aware datetimes
        aware_start = tz.localize(datetime.combine(start_date, start_time))
        aware_end = tz.localize(datetime.combine(end_date, end_time))

        # Make sure that start_date & end_date are within the period's
        # start_date & end_date
        if aware_start < period_start_date or aware_start > period_end_date:
            raise serializers.ValidationError({
                'start_date': [_(
                    "Start date must be set within the period's start_date "
                    "and end_date."
                )],
            })
        if aware_end < period_start_date or aware_end > period_end_date:
            raise serializers.ValidationError({
                'end_date': [_(
                    "End date must be set within the period's start_date "
                    "and end_date."
                )],
            })

        # Make sure that start_date is lower than end_date
        if aware_start >= aware_end:
            raise serializers.ValidationError({
                'end_date': [_("End date must be later than start_date.")],
                'start_date': [_("Start date must be earlier than end_date.")],
            })

        time_list = TimeSlot.objects.filter(
            period=validated_data['period']
        ).values_list('start_time', 'end_time')

        timeslot_data = {
            'period': validated_data['period'],
        }

        timeslot_data_list = list()

        # Create a list of start times for timeslots
        # Naive datetimes are used to avoid problems with DST (not handled by
        # rrule)
        timeslot_start_dates = list(
            rrule(
                freq=DAILY,
                dtstart=aware_start.replace(tzinfo=None),
                until=aware_end.replace(tzinfo=None),
                byweekday=validated_data['weekdays'],
            )
        )

        # Create a list of end times for timeslots
        # Naive datetimes are used to avoid problems with DST (not handled by
        # rrule)
        timeslot_end_dates = list(
            rrule(
                freq=DAILY,
                dtstart=aware_start.replace(
                    hour=aware_end.hour,
                    minute=aware_end.minute,
                    second=aware_end.second,
                    tzinfo=None,
                ),
                until=aware_end.replace(tzinfo=None),
                byweekday=validated_data['weekdays'],
            )
        )

        # For every start/end times in the list built by rrule, we add the
        # timezone information and create the timeslot using that timezone-
        # aware datetime. This will be automatically converted to correct UTC
        # time by Django.
        for start, end in zip(timeslot_start_dates, timeslot_end_dates):
            timeslot_data['start_time'] = tz.localize(start)
            timeslot_data['end_time'] = tz.localize(end)
            new_timeslot = TimeSlot(**timeslot_data)
            timeslot_data_list.append(new_timeslot)

        for duration in time_list:
            for timeslot in timeslot_data_list:
                start = timeslot.start_time
                end = timeslot.end_time
                if max(duration[0], start) < min(duration[1], end):
                    raise serializers.ValidationError({
                        'non_field_errors': _(
                            "An existing timeslot overlaps with the provided "
                            "start_time and end_time."
                        ),
                    })

        return timeslot_data_list

    def create(self, validated_data):
        return TimeSlot.objects.bulk_create(validated_data)

    def save(self, **kwargs):
        return self.create(self.validated_data)

    class Meta:
        model = TimeSlot
        exclude = ('deleted', 'price', 'users',)


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    # Custom names are needed to overcome an issue with DRF:
    # https://github.com/encode/django-rest-framework/issues/2719
    # I
    timeslot_details = TimeSlotSerializer(
        read_only=True,
        source='timeslot',
    )

    def validate(self, attrs):
        """Prevents overlapping and no-workplace reservations."""
        validated_data = super(ReservationSerializer, self).validate(attrs)

        action = self.context['view'].action

        if action == 'partial_update':
            # Only allow modification of is_present field.
            is_present = validated_data.get('is_present')
            if is_present is None or len(validated_data) > 1:
                raise serializers.ValidationError({
                    'is_present': _(
                        "Only is_present can be updated. To change other "
                        "fields, delete this reservation and create a new one."
                    ),
                })
            return attrs

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

    def to_representation(self, instance):
        user = self.context['request'].user
        volunteers = instance.timeslot.period.workplace.volunteers.all()

        is_staff = user.is_staff
        is_volunteer = user in volunteers

        if is_staff or is_volunteer:
            from blitz_api.serializers import ReservationUserSerializer
            self.fields['user_details'] = ReservationUserSerializer(
                source='user'
            )
        data = super(ReservationSerializer, self).to_representation(instance)

        if is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = Reservation
        exclude = ('deleted',)
        extra_kwargs = {
            'is_active': {
                'required': True,
                'help_text': _("Whether the reservation is active or not."),
            },
        }
