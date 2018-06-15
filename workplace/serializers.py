from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _

from location.models import Address
from location.serializers import AddressBasicSerializer

from .models import Workplace, Picture, Period, TimeSlot
from .fields import TimezoneField


class WorkplaceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    location = AddressBasicSerializer(
        # This overrides UniqueTogether constraint of the Address serializer
        validators=[],
        help_text=_("Address of the workplace."),
    )
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
        picture_urls = [picture.picture.url for picture in obj.pictures.all()]
        return [request.build_absolute_uri(url) for url in picture_urls]

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
                    raise serializers.ValidationError({
                        'detail': _(
                            "An active period associated to the same "
                            "workplace overlaps with the provided start_date "
                            "and end_date."
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
    id = serializers.ReadOnlyField()
    places_remaining = serializers.SerializerMethodField()

    def get_places_remaining(self, obj):
        seats = obj.period.workplace.seats
        reservations = obj.users.count()
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
