from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from decimal import Decimal
import random
import string
import uuid

from django.apps import apps
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, models
from django.db.models import Q
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from blitz_api.services import (remove_translation_fields,
                                check_if_translated_field,)
from workplace.models import Reservation
from retirement.models import Reservation as RetirementReservation
from retirement.models import WaitQueueNotification, Retirement

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, BaseProduct,
                     PaymentProfile, CustomPayment, Coupon, CouponUser, Refund,
                     )
from .services import (charge_payment,
                       create_external_payment_profile,
                       create_external_card,
                       get_external_cards,
                       PAYSAFE_CARD_TYPE,)

User = get_user_model()

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


class BaseProductSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    order_lines = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='orderline-detail'
    )
    price = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.1,
    )
    available = serializers.BooleanField(
        required=True,
    )
    name = serializers.CharField(
        required=False,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
    )

    def to_representation(self, instance):
        user = self.context['request'].user
        data = super(BaseProductSerializer, self).to_representation(instance)
        if not user.is_staff:
            data.pop("order_lines")
            data = remove_translation_fields(data)
        return data

    class Meta:
        model = BaseProduct
        fields = '__all__'
        abstract = True


class MembershipSerializer(BaseProductSerializer):

    def validate(self, attr):
        action = self.context['request'].parser_context['view'].action
        if action != 'partial_update':
            if not check_if_translated_field('name', attr):
                raise serializers.ValidationError({
                    'name': _("This field is required.")
                })
        return super(MembershipSerializer, self).validate(attr)

    class Meta:
        model = Membership
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the membership."),
                'validators': [
                    UniqueValidator(queryset=Membership.objects.all())
                ],
            },
        }


class PackageSerializer(BaseProductSerializer):
    reservations = serializers.IntegerField(
        min_value=1,
    )

    def validate(self, attr):
        action = self.context['request'].parser_context['view'].action
        if action != 'partial_update':
            if not check_if_translated_field('name', attr):
                raise serializers.ValidationError({
                    'name': _("This field is required.")
                })
        return super(PackageSerializer, self).validate(attr)

    class Meta:
        model = Package
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the package."),
                'validators': [
                    UniqueValidator(queryset=Package.objects.all())
                ],
            },
        }


class CustomPaymentSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    authorization_id = serializers.ReadOnlyField()
    settlement_id = serializers.ReadOnlyField()
    single_use_token = serializers.CharField(
        write_only=True,
        required=True,
    )

    def create(self, validated_data):
        """
        Create a custom payment and charge the user.
        """
        user = validated_data['user']
        single_use_token = validated_data.pop('single_use_token')
        # Temporary IDs until the external profile is created.
        validated_data['authorization_id'] = "0"
        validated_data['settlement_id'] = "0"
        validated_data['transaction_date'] = timezone.now()

        with transaction.atomic():
            custom_payment = CustomPayment.objects.create(**validated_data)
            amount = int(round(custom_payment.price*100))

            # Charge the order with the external payment API
            try:
                charge_response = charge_payment(
                    amount,
                    single_use_token,
                    str(custom_payment.id)
                )
            except PaymentAPIError as err:
                raise serializers.ValidationError({
                    'message': err
                })

            charge_res_content = charge_response.json()
            custom_payment.authorization_id = charge_res_content['id']
            custom_payment.settlement_id = charge_res_content[
                'settlements'
            ][0]['id']
            custom_payment.reference_number = charge_res_content[
                'merchantRefNum'
            ]
            custom_payment.save()

            # TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']

            items = [
                {
                    'price': custom_payment.price,
                    'name': custom_payment.name,
                }
            ]

            # Send custom_payment confirmation email
            merge_data = {
                'STATUS': "APPROUVÉE",
                'CARD_NUMBER': charge_res_content['card']['lastDigits'],
                'CARD_TYPE': PAYSAFE_CARD_TYPE[
                    charge_res_content['card']['type']
                ],
                'DATETIME': timezone.localtime().strftime("%x %X"),
                'ORDER_ID': custom_payment.id,
                'CUSTOMER_NAME': user.first_name + " " + user.last_name,
                'CUSTOMER_EMAIL': user.email,
                'CUSTOMER_NUMBER': user.id,
                'AUTHORIZATION': custom_payment.authorization_id,
                'TYPE': "Achat",
                'ITEM_LIST': items,
                # No tax applied on custom payments.
                'TAX': "0.00",
                'COST': custom_payment.price,
            }

            plain_msg = render_to_string("invoice.txt", merge_data)
            msg_html = render_to_string("invoice.html", merge_data)

            send_mail(
                "Confirmation d'achat",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [custom_payment.user.email],
                html_message=msg_html,
            )

            user.save()

            return custom_payment

    class Meta:
        model = CustomPayment
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the product."),
            },
            'transaction_date': {
                'read_only': True,
            },
        }


class PaymentProfileSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    cards = serializers.SerializerMethodField()

    def get_cards(self, obj):
        return get_external_cards(obj.external_api_id)

    class Meta:
        model = PaymentProfile
        fields = (
            'id',
            'name',
            'owner',
            'cards',
        )
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the payment profile."),
                'validators': [
                    UniqueValidator(queryset=PaymentProfile.objects.all())
                ],
            },
        }


class OrderLineSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model',
    )

    def validate(self, attrs):
        """Limits packages according to request user membership"""
        validated_data = super().validate(attrs)

        user = self.context['request'].user

        user_membership = user.membership
        user_academic_level = user.academic_level

        content_type = validated_data.get(
            'content_type',
            getattr(self.instance, 'content_type', None)
        )
        object_id = validated_data.get(
            'object_id',
            getattr(self.instance, 'object_id', None)
        )
        try:
            obj = content_type.get_object_for_this_type(pk=object_id)
        except content_type.model_class().DoesNotExist:
            raise serializers.ValidationError({
                'object_id': [
                    _("The referenced object does not exist.")
                ],
            })

        if (not user.is_staff
                and (content_type.model == 'package'
                     or content_type.model == 'retirement')
                and obj.exclusive_memberships.all()
                and user_membership not in obj.exclusive_memberships.all()):
            raise serializers.ValidationError({
                'object_id': [
                    _(
                        "User does not have the required membership to order "
                        "this package."
                    )
                ],
            })
        if (not user.is_staff and
                content_type.model == 'membership' and
                obj.academic_levels.all() and
                user_academic_level not in obj.academic_levels.all()):
            raise serializers.ValidationError({
                'object_id': [
                    _(
                        "User does not have the required academic_level to "
                        "order this membership."
                    )
                ],
            })

        return attrs

    class Meta:
        model = OrderLine
        fields = '__all__'


class OrderLineSerializerNoOrder(OrderLineSerializer):
    class Meta:
        model = OrderLine
        fields = '__all__'
        extra_kwargs = {
            'order': {
                'read_only': True,
            },
        }


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    authorization_id = serializers.ReadOnlyField()
    settlement_id = serializers.ReadOnlyField()
    order_lines = OrderLineSerializerNoOrder(many=True)
    payment_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True
    )
    single_use_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    coupon = serializers.SlugRelatedField(
        slug_field='code',
        queryset=Coupon.objects.all(),
        allow_null=True,
        required=False,
    )
    # target_user = serializers.HyperlinkedRelatedField(
    #     many=False,
    #     write_only=True,
    #     view_name='user-detail',
    #     required=False,
    #     allow_null=True,
    #     queryset=User.objects.all(),
    # )
    # save_card = serializers.NullBooleanField(
    #     write_only=True,
    #     required=False,
    # )

    def create(self, validated_data):
        """
        Create an Order and charge the user.
        """
        user = self.context['request'].user
        # if validated_data.get('target_user', None):
        #     if user.is_staff:
        #         user = validated_data.pop('target_user')
        #     else:
        #         raise serializers.ValidationError({
        #             'non_field_errors': [_(
        #                "You cannot create an order for another user without "
        #                 "admin rights."
        #             )]
        #         })
        orderlines_data = validated_data.pop('order_lines')
        payment_token = validated_data.pop('payment_token', None)
        single_use_token = validated_data.pop('single_use_token', None)
        # Temporary IDs until the external profile is created.
        validated_data['authorization_id'] = "0"
        validated_data['settlement_id'] = "0"
        validated_data['reference_number'] = "0"
        validated_data['transaction_date'] = timezone.now()
        validated_data['user'] = user
        profile = PaymentProfile.objects.filter(owner=user).first()

        retirement_reservations = list()

        if single_use_token and not profile:
            # Create external profile
            try:
                create_profile_response = create_external_payment_profile(
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
                external_api_id=create_profile_response.json()['id'],
                external_api_url='{0}{1}'.format(
                    create_profile_response.url,
                    create_profile_response.json()['id']
                )
            )

        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            charge_response = None
            discount_amount = 0
            for orderline_data in orderlines_data:
                OrderLine.objects.create(order=order, **orderline_data)
            amount = order.total_cost
            coupon = validated_data.get('coupon')
            if coupon:
                if (coupon.start_time > timezone.now()
                        or coupon.end_time < timezone.now()):
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "This coupon is only valid between {0} and {1}."
                            .format(
                                coupon.start_time.date(),
                                coupon.end_time.date()
                            )
                        )]
                    })
                if not (user.academic_program_code and user.faculty
                        and user.student_number):
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "Incomplete user profile. 'academic_program_code',"
                            " 'faculty' and 'student_number' fields must be "
                            "filled in the user profile to use a coupon."
                        )]
                    })
                coupon_user, created = CouponUser.objects.get_or_create(
                    coupon=coupon,
                    user=user,
                    defaults={'uses': 0},
                )
                total_coupon_uses = CouponUser.objects.filter(coupon=coupon)
                total_coupon_uses = sum(
                    total_coupon_uses.values_list('uses', flat=True)
                )
                valid_use = coupon_user.uses < coupon.max_use_per_user
                valid_use = valid_use or not coupon.max_use_per_user
                valid_use = valid_use and (total_coupon_uses < coupon.max_use
                                           or not coupon.max_use)
            if (coupon and valid_use):
                applicable_orderlines = order.order_lines.filter(
                    Q(content_type__in=coupon.applicable_product_types.all())
                    | Q(content_type__model='package',
                        object_id__in=coupon.applicable_packages.all().
                        values_list('id', flat=True))
                    | Q(content_type__model='timeslot',
                        object_id__in=coupon.applicable_timeslots.all().
                        values_list('id', flat=True))
                    | Q(content_type__model='membership',
                        object_id__in=coupon.applicable_memberships.all().
                        values_list('id', flat=True))
                    | Q(content_type__model='retirement',
                        object_id__in=coupon.applicable_retirements.all().
                        values_list('id', flat=True))
                )
                if applicable_orderlines:
                    most_exp_product = applicable_orderlines[0].content_object
                    for orderline in applicable_orderlines:
                        product = orderline.content_object
                        if product.price > most_exp_product.price:
                            most_exp_product = product
                    if not coupon.value:
                        discount_amount = most_exp_product.price
                    else:
                        discount_amount = min(
                            coupon.value,
                            most_exp_product.price
                        )
                    amount -= discount_amount
                    coupon_user.uses = coupon_user.uses + 1
                    coupon_user.save()
                else:
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "This coupon does not apply to any product."
                        )]
                    })
            # If coupon was provided but cannot be applied
            elif coupon:
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "Maximum number of uses exceeded for this coupon."
                    )]
                })

            tax = round(amount * Decimal(TAX_RATE), 2)
            amount *= Decimal(TAX_RATE + 1)
            amount = round(amount * 100, 2)

            membership_orderlines = order.order_lines.filter(
                content_type__model="membership"
            )
            package_orderlines = order.order_lines.filter(
                content_type__model="package"
            )
            reservation_orderlines = order.order_lines.filter(
                content_type__model="timeslot"
            )
            retirement_orderlines = order.order_lines.filter(
                content_type__model="retirement"
            )
            need_transaction = False

            if membership_orderlines:
                need_transaction = True
                today = timezone.now().date()
                if user.membership and user.membership_end > today:
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "You already have an active membership."
                        )]
                    })
                user.membership = membership_orderlines[0].content_object
                user.membership_end = (
                    timezone.now().date() + user.membership.duration
                )
            if package_orderlines:
                need_transaction = True
                for package_orderline in package_orderlines:
                    user.tickets += (
                        package_orderline.content_object.reservations *
                        package_orderline.quantity
                    )
            if reservation_orderlines:
                for reservation_orderline in reservation_orderlines:
                    timeslot = reservation_orderline.content_object
                    reserved = (
                        timeslot.reservations.filter(is_active=True).count()
                    )
                    if timeslot.price > user.tickets:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "You don't have enough tickets to make this "
                                "reservation."
                            )]
                        })
                    if (timeslot.period.workplace and
                            timeslot.period.workplace.seats - reserved > 0):
                        Reservation.objects.create(
                            user=user,
                            timeslot=timeslot,
                            is_active=True
                        )
                        # Decrement user tickets for each reservation.
                        # OrderLine's quantity and TimeSlot's price will be
                        # used in the future if we want to allow multiple
                        # reservations of the same timeslot.
                        user.tickets -= 1
                    else:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "There are no places left in the requested "
                                "timeslot."
                            )]
                        })
            if retirement_orderlines:
                need_transaction = True
                if not (user.phone and user.city):
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "Incomplete user profile. 'phone' and 'city' "
                            "field must be filled in the user profile to book "
                            "a retirement."
                        )]
                    })

                for retirement_orderline in retirement_orderlines:
                    retirement = retirement_orderline.content_object
                    user_waiting = retirement.wait_queue.filter(user=user)
                    reserved = (
                        retirement.reservations.filter(is_active=True).count()
                    )
                    if (((retirement.seats - retirement.total_reservations -
                          retirement.reserved_seats) > 0)
                            or (retirement.reserved_seats
                                and WaitQueueNotification.objects.filter(
                                    user=user, retirement=retirement))):
                        retirement_reservations.append(
                            RetirementReservation.objects.create(
                                user=user,
                                retirement=retirement,
                                order_line=retirement_orderline,
                                is_active=True
                            )
                        )
                    else:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "There are no places left in the requested "
                                "retirement."
                            )]
                        })
                    if user_waiting:
                        user_waiting.delete()

            if need_transaction and payment_token and int(amount):
                # Charge the order with the external payment API
                try:
                    charge_response = charge_payment(
                        int(amount),
                        payment_token,
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })

            elif need_transaction and single_use_token and int(amount):
                # Add card to the external profile & charge user
                try:
                    card_create_response = create_external_card(
                        profile.external_api_id,
                        single_use_token
                    )
                    charge_response = charge_payment(
                        int(amount),
                        card_create_response.json()['paymentToken'],
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })
            elif (membership_orderlines
                  or package_orderlines
                  or retirement_orderlines) and int(amount):
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "A payment_token or single_use_token is required to "
                        "create an order."
                    )]
                })

            if need_transaction:
                if charge_response:
                    charge_res_content = charge_response.json()
                    order.authorization_id = charge_res_content['id']
                    order.settlement_id = charge_res_content['settlements'][0][
                        'id'
                    ]
                    order.reference_number = charge_res_content[
                        'merchantRefNum'
                    ]
                else:
                    charge_res_content = {
                        'card': {
                            'lastDigits': None,
                            'type': "NONE"
                        }
                    }
                    order.authorization_id = 0
                    order.settlement_id = 0
                    order.reference_number = "charge-" + str(uuid.uuid4())
                order.save()

                orderlines = order.order_lines.filter(
                    models.Q(content_type__model='membership') |
                    models.Q(content_type__model='package') |
                    models.Q(content_type__model='retirement')
                )

                # Here, the 'details' key is used to provide details of the
                #  item to the email template.
                # As of now, only 'retirement' objects have the 'email_content'
                #  key that is used here. There is surely a better way to
                #  to handle that logic that will be more generic.
                items = [
                    {
                        'price': orderline.content_object.price,
                        'name': "{0}: {1}".format(
                            str(orderline.content_type),
                            orderline.content_object.name
                        ),
                        # Removed details section because it was only used
                        # for retirements. Retirements instead have another
                        # unique email containing details of the event.
                        # 'details':
                        #    orderline.content_object.email_content if hasattr(
                        #         orderline.content_object, 'email_content'
                        #     ) else ""
                    } for orderline in orderlines
                ]

                # Send order confirmation email
                merge_data = {
                    'STATUS': "APPROUVÉE",
                    'CARD_NUMBER': charge_res_content['card']['lastDigits'],
                    'CARD_TYPE': PAYSAFE_CARD_TYPE[
                        charge_res_content['card']['type']
                    ],
                    'DATETIME': timezone.localtime().strftime("%x %X"),
                    'ORDER_ID': order.id,
                    'CUSTOMER_NAME': user.first_name + " " + user.last_name,
                    'CUSTOMER_EMAIL': user.email,
                    'CUSTOMER_NUMBER': user.id,
                    'AUTHORIZATION': order.authorization_id,
                    'TYPE': "Achat",
                    'ITEM_LIST': items,
                    'TAX': tax,
                    'DISCOUNT': discount_amount,
                    'COUPON': coupon,
                    'SUBTOTAL': round(amount / 100 - tax, 2),
                    'COST': round(Decimal(amount) / 100, 2),
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

            for retirement_reservation in retirement_reservations:
                # Send info email
                merge_data = {
                    'RETIREMENT': retirement_reservation.retirement,
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
                    [retirement_reservation.user.email],
                    html_message=msg_html,
                )

            user.save()

            return order

    def update(self, instance, validated_data):
        orderlines_data = validated_data.pop('order_lines')
        order = super().update(instance, validated_data)
        for orderline_data in orderlines_data:
            OrderLine.objects.update_or_create(
                order=order,
                content_type=orderline_data.get('content_type'),
                object_id=orderline_data.get('object_id'),
                defaults=orderline_data,
            )
        return order

    class Meta:
        model = Order
        fields = '__all__'
        extra_kwargs = {
            'transaction_date': {
                'read_only': True,
            },
            'user': {
                'read_only': True,
            },
        }


class CouponSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    applicable_product_types = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model',
        many=True,
        required=False,
    )
    code = serializers.ReadOnlyField()
    value = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.0,
    )
    max_use = serializers.IntegerField(
        min_value=0
    )
    max_use_per_user = serializers.IntegerField(
        min_value=0
    )

    def create(self, validated_data):
        """
        Generate coupon's code and create the coupon.
        """
        code = ""
        n = 0
        used_code = Coupon.objects.all().values_list('code', flat=True)
        while ((not code or code in used_code) and (n < 100)):
            code = ''.join(
                random.choices(
                    string.ascii_uppercase.replace("O", "").replace("I", "") +
                    string.digits.replace("0", ""),
                    k=8))
            n += 1
        if n >= 100:
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "Can't generate new unique codes. Delete old coupons."
                )]
            })
        validated_data['code'] = code
        return super(CouponSerializer, self).create(validated_data)

    class Meta:
        model = Coupon
        exclude = ('deleted', )
        extra_kwargs = {
            'applicable_retirements': {
                'required': False,
            },
            'applicable_timeslots': {
                'required': False,
            },
            'applicable_packages': {
                'required': False,
            },
            'applicable_memberships': {
                'required': False,
            },
        }


class RefundSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Refund
        exclude = ('deleted', )
