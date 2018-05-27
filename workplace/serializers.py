from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _

from location.models import Address
from location.serializers import AddressBasicSerializer

from .models import Workplace, Picture, Period, TimeSlot


class WorkplaceSerializer(serializers.HyperlinkedModelSerializer):
    location = AddressBasicSerializer(
        # This overrides UniqueTogether constraint of the Address serializer
        validators=[],
        help_text=_("Address of the workplace."),
    )

    def validate_location(self, value):
        """
        Checks that the address exists. Since the AddressBasicSerializer
        returns a dictionary containing the address' informations, we
        unpack that dictionary as kwargs for the Address model query.
        """
        address = Address.objects.filter(**value)

        if address:
            return address[0]
        raise serializers.ValidationError(
            _("This address does not exist.")
        )

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

    def validate(self, attrs):
        """Prevents overlapping periods and invalid start/end date"""
        start = attrs['start_date']
        end = attrs['end_date']

        if start >= end:
            raise serializers.ValidationError({
                'end_date': [_("End date must be later than start_date.")],
                'start_date': [_("End date must be earlier than end_date.")],
            })

        # Generate a list of tuples containing start/end date of existing
        # periods in the requested workplace.
        existing_periods = Period.objects.filter(
            workplace=attrs['workplace']
        ).values_list('start_date', 'end_date')

        for periods in existing_periods:
            if max(periods[0], start) < min(periods[1], end):
                raise serializers.ValidationError({
                    'detail': _(
                        "An existing period overlaps with the provided "
                        "start_date and end_date."
                    ),
                })

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

    def validate(self, attrs):
        """Prevents overlapping timeslots and invalid start/end time"""
        start = attrs['start_time']
        end = attrs['end_time']

        if start >= end:
            raise serializers.ValidationError({
                'end_time': [_("End time must be later than start_time.")],
                'start_time': [_("End time must be earlier than end_time.")],
            })

        # Generate a list of tuples containing start/end time of existing
        # timeslots in the requested period.
        existing_timeslot = TimeSlot.objects.filter(
            period=attrs['period']
        ).values_list('start_time', 'end_time')

        for timeslots in existing_timeslot:
            if max(timeslots[0], start) < min(timeslots[1], end):
                raise serializers.ValidationError({
                    'detail': _(
                        "An existing timeslot overlaps with the provided "
                        "start_time and end_time."
                    ),
                })

        if 'users' in attrs:
            for user in attrs['users']:
                # Generate a list of tuples containing start/end time of
                # existing timeslots in the requested user.
                existing_timeslot = TimeSlot.objects.filter(
                    users=user
                ).values_list('start_time', 'end_time')

                for timeslots in existing_timeslot:
                    if max(timeslots[0], start) < min(timeslots[1], end):
                        raise serializers.ValidationError({
                            'detail': _(
                                "The user has an overlapping timeslot."
                            ),
                        })

        return attrs

    def create(self, validated_data):
        """
        Uses period's price if no price is provided.
        """
        if 'price' not in validated_data:
            validated_data['price'] = validated_data['period'].price

        return super().create(validated_data)

    class Meta:
        model = TimeSlot
        fields = '__all__'
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
