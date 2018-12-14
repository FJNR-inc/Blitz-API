from copy import copy

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers, status
from rest_framework.reverse import reverse
from rest_framework.validators import UniqueValidator

from blitz_api.serializers import UserSerializer
from blitz_api.services import (check_if_translated_field,
                                remove_translation_fields)

from .fields import TimezoneField
from .models import (Picture, Reservation, Retirement, WaitQueue,
                     WaitQueueNotification, )

User = get_user_model()


class RetirementSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    places_remaining = serializers.SerializerMethodField()
    total_reservations = serializers.ReadOnlyField()
    reservations = serializers.SerializerMethodField()
    reservations_canceled = serializers.SerializerMethodField()
    timezone = TimezoneField(
        required=False,
        help_text=_("Timezone of the workplace."),
    )
    name = serializers.CharField(
        required=False,
        validators=[UniqueValidator(queryset=Retirement.objects.all())],
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Retirement.objects.all())],
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Retirement.objects.all())],
    )
    details = serializers.CharField(required=False, )
    country = serializers.CharField(required=False, )
    state_province = serializers.CharField(required=False, )
    city = serializers.CharField(required=False, )
    address_line1 = serializers.CharField(required=False, )

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

    def get_reservations(self, obj):
        reservation_ids = Reservation.objects.filter(
            is_active=True,
            retirement=obj,
        ).values_list(
            'id',
            flat=True,
        )
        return [
            reverse(
                'retirement:reservation-detail',
                args=[id],
                request=self.context['request'],
            ) for id in reservation_ids
        ]

    def get_reservations_canceled(self, obj):
        reservation_ids = Reservation.objects.filter(
            is_active=False,
            retirement=obj,
        ).values_list(
            'id',
            flat=True,
        )
        return [
            reverse(
                'retirement:reservation-detail',
                args=[id],
                request=self.context['request'],
            ) for id in reservation_ids
        ]

    def get_places_remaining(self, obj):
        seats = obj.seats
        reserved_seats = obj.reserved_seats
        reservations = obj.reservations.filter(is_active=True).count()
        return seats - reservations - reserved_seats

    def validate(self, attr):
        err = {}
        if not check_if_translated_field('name', attr):
            err['name'] = _("This field is required.")
        if not check_if_translated_field('details', attr):
            err['details'] = _("This field is required.")
        if not check_if_translated_field('country', attr):
            err['country'] = _("This field is required.")
        if not check_if_translated_field('state_province', attr):
            err['state_province'] = _("This field is required.")
        if not check_if_translated_field('city', attr):
            err['city'] = _("This field is required.")
        if not check_if_translated_field('address_line1', attr):
            err['address_line1'] = _("This field is required.")
        if not check_if_translated_field('timezone', attr):
            err['timezone'] = _("This field is required.")
        if not check_if_translated_field('postal_code', attr):
            err['postal_code'] = _("This field is required.")
        if not check_if_translated_field('seats', attr):
            err['seats'] = _("This field is required.")
        if not check_if_translated_field('price', attr):
            err['price'] = _("This field is required.")
        if not check_if_translated_field('start_time', attr):
            err['start_time'] = _("This field is required.")
        if not check_if_translated_field('end_time', attr):
            err['end_time'] = _("This field is required.")
        if not check_if_translated_field('min_day_refund', attr):
            err['min_day_refund'] = _("This field is required.")
        if not check_if_translated_field('refund_rate', attr):
            err['refund_rate'] = _("This field is required.")
        if not check_if_translated_field('min_day_exchange', attr):
            err['min_day_exchange'] = _("This field is required.")
        if not check_if_translated_field('is_active', attr):
            err['is_active'] = _("This field is required.")
        if err:
            raise serializers.ValidationError(err)
        return super(RetirementSerializer, self).validate(attr)

    def to_representation(self, instance):
        is_staff = self.context['request'].user.is_staff
        if self.context['view'].action == 'retrieve' and is_staff:
            self.fields['users'] = UserSerializer(many=True)
        data = super(RetirementSerializer, self).to_representation(instance)
        if is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = Retirement
        exclude = ('deleted', )
        extra_kwargs = {
            'details': {
                'help_text': _("Description of the retirement.")
            },
            'name': {
                'help_text': _("Name of the retirement."),
                'validators':
                [UniqueValidator(queryset=Retirement.objects.all())],
            },
            'seats': {
                'required': False,
                'help_text': _("Number of available seats.")
            },
            'timezone': {
                'required': False,
            },
            'end_time': {
                'required': False,
            },
            'start_time': {
                'required': False,
            },
            'postal_code': {
                'required': False,
            },
            'refund_rate': {
                'required': False,
            },
            'min_day_exchange': {
                'required': False,
            },
            'min_day_refund': {
                'required': False,
            },
            'price': {
                'required': False,
            },
            'url': {
                'view_name': 'retirement:retirement-detail',
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
            'retirement': {
                'help_text': _("Retirement represented by the picture."),
                'view_name': 'retirement:retirement-detail',
            },
            'url': {
                'view_name': 'retirement:picture-detail',
            },
            'name': {
                'help_text': _("Name of the picture."),
            },
            'picture': {
                'help_text': _("File to upload."),
            }
        }


class ReservationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    # Custom names are needed to overcome an issue with DRF:
    # https://github.com/encode/django-rest-framework/issues/2719
    # I
    retirement_details = RetirementSerializer(
        read_only=True,
        source='retirement',
    )
    user_details = UserSerializer(
        read_only=True,
        source='user',
    )

    def validate(self, attrs):
        """Prevents overlapping reservations."""
        validated_data = super(ReservationSerializer, self).validate(attrs)

        action = self.context['view'].action

        if action == 'partial_update':
            # Only allow modification of is_present field.
            is_present = validated_data.get('is_present')
            if is_present is None or len(validated_data) > 1:
                raise serializers.ValidationError({
                    'is_present':
                    _("Only is_present can be updated. To change other "
                      "fields, delete this reservation and create a new one."),
                })
            return attrs

        # Generate a list of tuples containing start/end time of
        # existing reservations.
        start = validated_data['retirement'].start_time
        end = validated_data['retirement'].end_time
        active_reservations = Reservation.objects.filter(
            user=validated_data['user'],
            is_active=True,
        ).exclude(**validated_data).values_list(
            'retirement__start_time',
            'retirement__end_time',
        )

        for retirements in active_reservations:
            if max(retirements[0], start) < min(retirements[1], end):
                raise serializers.ValidationError(
                    'This reservation overlaps with another active '
                    'reservations for this user.')
        return attrs

    class Meta:
        model = Reservation
        exclude = ('deleted', )
        extra_kwargs = {
            'retirement': {
                'help_text': _("Retirement represented by the picture."),
                'view_name': 'retirement:retirement-detail',
            },
            'is_active': {
                'required': True,
                'help_text': _("Whether the reservation is active or not."),
            },
            'url': {
                'view_name': 'retirement:reservation-detail',
            },
        }


class WaitQueueSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()

    def validate_user(self, obj):
        """
        Subscribe the authenticated user.
        If the authenticated user is an admin (is_staff), use the user provided
        in the request's 'user' field.
        """
        if self.context['request'].user.is_staff:
            return obj
        return self.context['request'].user

    class Meta:
        model = WaitQueue
        fields = '__all__'
        extra_kwargs = {
            'retirement': {
                'view_name': 'retirement:retirement-detail',
            },
            'url': {
                'view_name': 'retirement:waitqueue-detail',
            },
        }


class WaitQueueNotificationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()

    class Meta:
        model = WaitQueue
        fields = '__all__'
        extra_kwargs = {
            'retirement': {
                'view_name': 'retirement:retirement-detail',
            },
            'url': {
                'view_name': 'retirement:waitqueuenotification-detail',
            },
        }
