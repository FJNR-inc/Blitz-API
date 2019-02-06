from copy import copy
from datetime import timedelta
from decimal import Decimal, DecimalException
import json
import requests
import traceback

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import mail_admins
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
from store.exceptions import PaymentAPIError
from store.models import Order, OrderLine, PaymentProfile, Refund
from store.services import (charge_payment,
                            create_external_payment_profile,
                            create_external_card,
                            get_external_cards,
                            PAYSAFE_CARD_TYPE,
                            PAYSAFE_EXCEPTION,
                            refund_amount, )

from .fields import TimezoneField
from .models import (Picture, Reservation, Retirement, WaitQueue,
                     WaitQueueNotification, )
from .services import refund_retirement

User = get_user_model()

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


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

    def validate_refund_rate(self, value):
        if value > 100:
            raise serializers.ValidationError(_(
                "Refund rate must be between 0 and 100 (%)."
            ))
        return value

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
        if not check_if_translated_field('accessibility', attr):
            err['accessibility'] = _("This field is required.")
        if err:
            raise serializers.ValidationError(err)
        return super(RetirementSerializer, self).validate(attr)

    def create(self, validated_data):
        """
        Schedule retirement reminder and post-event emails.
        UPDATE: Commenting out reminder email since they are no longer desired.
        """
        retirement = super().create(validated_data)

        scheduler_url = '{0}'.format(
            settings.EXTERNAL_SCHEDULER['URL'],
        )

        # Set reminder email
        # reminder_date = validated_data['start_time'] - timedelta(days=7)
        #
        # data = {
        #     "hour": 8,
        #     "minute": 0,
        #     "day_of_month": reminder_date.day,
        #     "month": reminder_date.month,
        #     "url": '{0}{1}'.format(
        #         self.context['request'].build_absolute_uri(
        #             reverse(
        #                 'retirement:retirement-detail',
        #                 args=(retirement.id, )
        #             )
        #         ),
        #         "/remind_users"
        #     ),
        #     "description": "Retirement 7-days reminder notification"
        # }
        #
        # try:
        #     auth_data = {
        #         "username": settings.EXTERNAL_SCHEDULER['USER'],
        #         "password": settings.EXTERNAL_SCHEDULER['PASSWORD']
        #     }
        #     auth = requests.post(
        #         scheduler_url + "/authentication",
        #         json=auth_data,
        #     )
        #     auth.raise_for_status()
        #
        #     r = requests.post(
        #         scheduler_url + "/tasks",
        #         json=data,
        #         headers={
        #             'Authorization':
        #             'Token ' + json.loads(auth.content)['token']},
        #     )
        #     r.raise_for_status()
        # except (requests.exceptions.HTTPError,
        #         requests.exceptions.ConnectionError) as err:
        #     mail_admins(
        #         "Thèsez-vous: external scheduler error",
        #         "{0}\nRetirement:{1}\nException:\n{2}\n".format(
        #             "Pre-event email task scheduling failed!",
        #             retirement.__dict__,
        #             traceback.format_exc(),
        #         )
        #     )

        # Set post-event email
        # Send the email at midnight the next day.
        throwback_date = validated_data['end_time'] + timedelta(days=1)

        data = {
            "hour": 0,
            "minute": 0,
            "day_of_month": throwback_date.day,
            "month": throwback_date.month,
            "url": '{0}{1}'.format(
                self.context['request'].build_absolute_uri(
                    reverse(
                        'retirement:retirement-detail',
                        args=(retirement.id, )
                    )
                ),
                "/recap"
            ),
            "description": "Retirement post-event notification"
        }

        try:
            auth_data = {
                "username": settings.EXTERNAL_SCHEDULER['USER'],
                "password": settings.EXTERNAL_SCHEDULER['PASSWORD']
            }
            auth = requests.post(
                scheduler_url + "/authentication",
                json=auth_data,
            )
            auth.raise_for_status()

            r = requests.post(
                scheduler_url + "/tasks",
                json=data,
                headers={
                    'Authorization':
                    'Token ' + json.loads(auth.content)['token']},
                timeout=(10, 10),
            )
            r.raise_for_status()
        except (requests.exceptions.HTTPError,
                requests.exceptions.ConnectionError) as err:
            mail_admins(
                "Thèsez-vous: external scheduler error",
                "{0}\nRetirement:{1}\nException:\n{2}\n".format(
                    "Post-event email task scheduling failed!",
                    retirement.__dict__,
                    traceback.format_exc(),
                )
            )

        return retirement

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
    payment_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    single_use_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs):
        """Prevents overlapping reservations."""
        validated_data = super(ReservationSerializer, self).validate(attrs)

        action = self.context['view'].action

        # This validation is here instead of being in the 'update()' method
        # because we need to stop validation if improper fields are passed in
        # a partial update.
        if action == 'partial_update':
            # Only allow modification of is_present & retirement fields.
            is_invalid = validated_data.copy()
            is_invalid.pop('is_present', None)
            is_invalid.pop('retirement', None)
            is_invalid.pop('payment_token', None)
            is_invalid.pop('single_use_token', None)
            if is_invalid:
                raise serializers.ValidationError({
                    'non_field_errors': [
                        _("Only is_present and retirement can be updated. To "
                          "change other fields, delete this reservation and "
                          "create a new one.")
                    ]
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
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "This reservation overlaps with another active "
                        "reservations for this user."
                    )]
                })
        return attrs

    def update(self, instance, validated_data):
        user = instance.user
        payment_token = validated_data.pop('payment_token', None)
        single_use_token = validated_data.pop('single_use_token', None)
        need_transaction = False
        need_refund = False
        amount = 0
        profile = PaymentProfile.objects.filter(owner=user).first()
        instance_pk = instance.pk
        current_retirement = instance.retirement
        coupon = instance.order_line.coupon
        coupon_value = instance.order_line.coupon_real_value
        order_line = instance.order_line
        request = self.context['request']

        if not self.context['request'].user.is_staff:
            validated_data.pop('is_present', None)

        if not instance.is_active:
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "This reservation has already been canceled."
                )]
            })

        with transaction.atomic():
            # Create a copy of the reservation. This copy keeps track of
            # the exchange.
            canceled_reservation = instance
            canceled_reservation.pk = None
            canceled_reservation.save()

            instance = Reservation.objects.get(id=instance_pk)

            canceled_reservation.is_active = False
            canceled_reservation.cancelation_reason = 'U'
            canceled_reservation.cancelation_action = 'E'
            canceled_reservation.cancelation_date = timezone.now()
            canceled_reservation.save()

            # Update the reservation
            instance = super(ReservationSerializer, self).update(
                instance,
                validated_data,
            )

            # Update retirement seats
            free_seats = (
                current_retirement.seats -
                current_retirement.total_reservations
            )
            if (current_retirement.reserved_seats or free_seats == 1):
                current_retirement.reserved_seats += 1
                current_retirement.save()

            if validated_data.get('retirement'):
                # Validate if user has the right to reserve a seat in the new
                # retirement
                new_retirement = instance.retirement
                old_retirement = current_retirement

                user_waiting = new_retirement.wait_queue.filter(user=user)
                free_seats = (
                    new_retirement.seats -
                    new_retirement.total_reservations -
                    new_retirement.reserved_seats +
                    1
                )
                reserved_for_user = (
                    new_retirement.reserved_seats and
                    WaitQueueNotification.objects.filter(
                        user=user,
                        retirement=new_retirement
                    )
                )
                if not (free_seats > 0 or reserved_for_user):
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "There are no places left in the requested "
                            "retirement."
                        )]
                    })
                if user_waiting:
                    user_waiting.delete()

            if (self.context['view'].action == 'partial_update' and
                    validated_data.get('retirement')):
                if order_line.quantity > 1:
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "The order containing this reservation has a "
                            "quantity bigger than 1. Please contact the "
                            "support team."
                        )]
                    })
                days_remaining = current_retirement.start_time - timezone.now()
                days_exchange = timedelta(
                    days=current_retirement.min_day_exchange
                )
                respects_minimum_days = (days_remaining >= days_exchange)
                new_retirement_price = validated_data['retirement'].price
                if current_retirement.price < new_retirement_price:
                    # If the new retirement is more expensive, reapply the
                    # coupon on the new orderline created. In other words, any
                    # coupon used for the initial purchase is applied again
                    # here.
                    need_transaction = True
                    amount = (
                        validated_data['retirement'].price -
                        order_line.coupon_real_value
                    )
                    if not (payment_token or single_use_token):
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "The new retirement is more expensive than "
                                "the current one. Provide a payment_token or "
                                "single_use_token to charge the balance."
                            )]
                        })
                if current_retirement.price > new_retirement_price:
                    # If a coupon was applied for the purchase, check if the
                    # real cost of the purchase was lower than the price
                    # difference.
                    # If so, refund the real cost of the purchase.
                    # Else refund the difference between the 2 retirements.
                    need_refund = True
                    price_diff = (
                        current_retirement.price -
                        validated_data['retirement'].price
                    )
                    real_cost = order_line.cost
                    amount = min(price_diff, real_cost)
                if current_retirement == validated_data['retirement']:
                    raise serializers.ValidationError({
                        'retirement': [_(
                            "That retirement is already assigned to this "
                            "object."
                        )]
                    })
                if not respects_minimum_days:
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "Maximum exchange date exceeded."
                        )]
                    })
                if need_transaction and (single_use_token and not profile):
                    # Create external profile
                    try:
                        create_profile_res = create_external_payment_profile(
                            user
                        )
                    except PaymentAPIError as err:
                        raise serializers.ValidationError({
                            'message': err
                        })
                    # Create local profile
                    profile = PaymentProfile.objects.create(
                        name="Paysafe",
                        owner=user,
                        external_api_id=create_profile_res.json()['id'],
                        external_api_url='{0}{1}'.format(
                            create_profile_res.url,
                            create_profile_res.json()['id']
                        )
                    )
                # Generate a list of tuples containing start/end time of
                # existing reservations.
                start = validated_data['retirement'].start_time
                end = validated_data['retirement'].end_time
                active_reservations = Reservation.objects.filter(
                    user=user,
                    is_active=True,
                ).exclude(pk=instance.pk).values_list(
                    'retirement__start_time',
                    'retirement__end_time',
                )

                for retirements in active_reservations:
                    if max(retirements[0], start) < min(retirements[1], end):
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "This reservation overlaps with another "
                                "active reservations for this user."
                            )]
                        })
                if need_transaction:
                    order = Order.objects.create(
                        user=user,
                        transaction_date=timezone.now(),
                        authorization_id=1,
                        settlement_id=1,
                    )
                    new_order_line = OrderLine.objects.create(
                        order=order,
                        quantity=1,
                        content_type=ContentType.objects.get_for_model(
                            Retirement
                        ),
                        object_id=validated_data['retirement'].id,
                        cost=amount,
                        coupon=coupon,
                        coupon_real_value=coupon_value,
                    )
                    tax = round(amount * Decimal(TAX_RATE), 2)
                    amount *= Decimal(TAX_RATE + 1)
                    amount = round(amount * 100, 2)
                    retirement = validated_data['retirement']

                    # Do a complete refund of the previous retirement
                    try:
                        refund_instance = refund_retirement(
                            canceled_reservation,
                            100,
                            "Exchange retirement {0} for retirement "
                            "{1}".format(
                                str(current_retirement),
                                str(validated_data['retirement'])
                            )
                        )
                    except PaymentAPIError as err:
                        if str(err) == PAYSAFE_EXCEPTION['3406']:
                            raise serializers.ValidationError({
                                'non_field_errors': _(
                                    "The order has not been charged yet. "
                                    "Try again later."
                                )
                            })
                        raise serializers.ValidationError({
                            'message': str(err)
                        })

                    if payment_token and int(amount):
                        # Charge the order with the external payment API
                        try:
                            charge_response = charge_payment(
                                int(round(amount)),
                                payment_token,
                                str(order.id)
                            )
                        except PaymentAPIError as err:
                            raise serializers.ValidationError({
                                'message': err
                            })

                    elif single_use_token and int(amount):
                        # Add card to the external profile & charge user
                        try:
                            card_create_response = create_external_card(
                                profile.external_api_id,
                                single_use_token
                            )
                            charge_response = charge_payment(
                                int(round(amount)),
                                card_create_response.json()['paymentToken'],
                                str(order.id)
                            )
                        except PaymentAPIError as err:
                            raise serializers.ValidationError({
                                'message': err
                            })
                    charge_res_content = charge_response.json()
                    order.authorization_id = charge_res_content['id']
                    order.settlement_id = charge_res_content['settlements'][0][
                        'id'
                    ]
                    order.reference_number = charge_res_content[
                        'merchantRefNum'
                    ]
                    order.save()
                    instance.order_line = new_order_line
                    instance.save()

                if need_refund:
                    tax = round(amount * Decimal(TAX_RATE), 2)
                    amount *= Decimal(TAX_RATE + 1)
                    amount = round(amount * 100, 2)
                    retirement = validated_data['retirement']

                    refund_instance = Refund.objects.create(
                        orderline=order_line,
                        refund_date=timezone.now(),
                        amount=amount/100,
                        details="Exchange retirement {0} for "
                                "retirement {1}".format(
                                    str(current_retirement),
                                    str(validated_data['retirement'])
                                ),
                    )

                    try:
                        refund_response = refund_amount(
                            order_line.order.settlement_id,
                            int(round(amount))
                        )
                        refund_res_content = refund_response.json()
                        refund_instance.refund_id = refund_res_content['id']
                        refund_instance.save()
                    except PaymentAPIError as err:
                        if str(err) == PAYSAFE_EXCEPTION['3406']:
                            raise serializers.ValidationError({
                                'non_field_errors': _(
                                    "The order has not been charged yet. "
                                    "Try again later."
                                )
                            })
                        raise serializers.ValidationError({
                            'message': str(err)
                        })

                    new_retirement = retirement
                    old_retirement = current_retirement

            # Ask the external scheduler to start calling /notify if the
            # reserved_seats count == 1. Otherwise, the scheduler should
            # already be calling /notify at specified intervals.
            #
            # Since we are in the context of a cancelation, if reserved_seats
            # equals 1, that means that this is the first cancelation.
            if current_retirement.reserved_seats == 1:
                scheduler_url = '{0}'.format(
                    settings.EXTERNAL_SCHEDULER['URL'],
                )

                data = {
                    "hour": timezone.now().hour,
                    "minute": (timezone.now().minute + 5) % 60,
                    "url": '{0}{1}'.format(
                        request.build_absolute_uri(
                            reverse('retirement:waitqueuenotification-list')
                        ),
                        "/notify"
                    ),
                    "description": "Retirement wait queue notification"
                }

                try:
                    auth_data = {
                        "username": settings.EXTERNAL_SCHEDULER['USER'],
                        "password": settings.EXTERNAL_SCHEDULER['PASSWORD']
                    }
                    auth = requests.post(
                        scheduler_url + "/authentication",
                        json=auth_data,
                    )
                    auth.raise_for_status()

                    r = requests.post(
                        scheduler_url + '/tasks',
                        json=data,
                        headers={
                            'Authorization':
                            'Token ' + json.loads(auth.content)['token']},
                        timeout=(10, 10),
                    )
                    r.raise_for_status()
                except (requests.exceptions.HTTPError,
                        requests.exceptions.ConnectionError) as err:
                    mail_admins(
                        "Thèsez-vous: external scheduler error",
                        traceback.format_exc()
                    )

        # Send appropriate emails
        # Send order confirmation email
        if need_transaction:
            items = [
                {
                    'price': new_order_line.content_object.price,
                    'name': "{0}: {1}".format(
                        str(new_order_line.content_type),
                        new_order_line.content_object.name
                    ),
                }
            ]

            merge_data = {
                'STATUS': "APPROUVÉE",
                'CARD_NUMBER':
                charge_res_content['card']['lastDigits'],
                'CARD_TYPE': PAYSAFE_CARD_TYPE[
                    charge_res_content['card']['type']
                ],
                'DATETIME': timezone.localtime().strftime("%x %X"),
                'ORDER_ID': order.id,
                'CUSTOMER_NAME':
                    user.first_name + " " + user.last_name,
                'CUSTOMER_EMAIL': user.email,
                'CUSTOMER_NUMBER': user.id,
                'AUTHORIZATION': order.authorization_id,
                'TYPE': "Achat",
                'ITEM_LIST': items,
                'TAX': round(
                    (new_order_line.cost - current_retirement.price) *
                    Decimal(TAX_RATE),
                    2,
                ),
                'DISCOUNT': current_retirement.price,
                'COUPON': {'code': _("Échange")},
                'SUBTOTAL': round(
                    new_order_line.cost - current_retirement.price,
                    2
                ),
                'COST': round(
                    (new_order_line.cost - current_retirement.price) *
                    Decimal(TAX_RATE + 1),
                    2
                ),
            }

            plain_msg = render_to_string("invoice.txt", merge_data)
            msg_html = render_to_string("invoice.html", merge_data)

            send_mail(
                "Confirmation d'achat",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
                html_message=msg_html,
            )

        # Send refund confirmation email
        if need_refund:
            merge_data = {
                'DATETIME': timezone.localtime().strftime("%x %X"),
                'ORDER_ID': order_line.order.id,
                'CUSTOMER_NAME':
                user.first_name + " " + user.last_name,
                'CUSTOMER_EMAIL': user.email,
                'CUSTOMER_NUMBER': user.id,
                'TYPE': "Remboursement",
                'NEW_RETIREMENT': new_retirement,
                'OLD_RETIREMENT': old_retirement,
                'SUBTOTAL':
                old_retirement.price - new_retirement.price,
                'COST': round(amount/100, 2),
                'TAX': round(Decimal(tax), 2),
            }

            plain_msg = render_to_string("refund.txt", merge_data)
            msg_html = render_to_string("refund.html", merge_data)

            send_mail(
                "Confirmation de remboursement",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=msg_html,
            )

        # Send exchange confirmation email
        if validated_data.get('retirement'):
            merge_data = {
                'DATETIME': timezone.localtime().strftime("%x %X"),
                'CUSTOMER_NAME': user.first_name + " " + user.last_name,
                'CUSTOMER_EMAIL': user.email,
                'CUSTOMER_NUMBER': user.id,
                'TYPE': "Échange",
                'NEW_RETIREMENT': new_retirement,
                'OLD_RETIREMENT': old_retirement,
            }

            plain_msg = render_to_string("exchange.txt", merge_data)
            msg_html = render_to_string("exchange.html", merge_data)

            send_mail(
                "Confirmation d'échange",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=msg_html,
            )

            merge_data = {
                'RETIREMENT': new_retirement,
                'USER': instance.user,
            }

            plain_msg = render_to_string(
                "retirement_info.txt",
                merge_data
            )
            msg_html = render_to_string(
                "retirement_info.html",
                merge_data
            )

            send_mail(
                "Confirmation d'inscription à la retraite",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                html_message=msg_html,
            )

        return Reservation.objects.get(id=instance_pk)

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
