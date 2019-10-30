import json
from datetime import timedelta, date

from dateutil.relativedelta import relativedelta
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.fields import empty
from rest_framework.serializers import as_serializer_error
from rest_framework.settings import api_settings
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
                                check_if_translated_field,
                                getMessageTranslate)
from log_management.models import Log
from workplace.models import Reservation
from retirement.models import Reservation as RetreatReservation, \
    RetreatInvitation
from retirement.models import WaitQueueNotification, Retreat

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, BaseProduct,
                     PaymentProfile, CustomPayment, Coupon, CouponUser, Refund,
                     MembershipCoupon, OptionProduct, OrderLineBaseProduct)
from .services import (charge_payment,
                       create_external_payment_profile,
                       create_external_card,
                       get_external_cards,
                       PAYSAFE_CARD_TYPE,
                       validate_coupon_for_order, )

User = get_user_model()

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


class BaseProductManagerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = BaseProduct
        fields = '__all__'

    def to_representation(self, instance):

        instance = BaseProduct.objects.get_subclass(id=instance.id)

        if isinstance(instance, Retreat):
            from retirement.serializers import RetreatSerializer
            serializer = RetreatSerializer
        elif isinstance(instance, OptionProduct):
            serializer = OptionProductSerializer
        elif isinstance(instance, Membership):
            serializer = MembershipSerializer
        elif isinstance(instance, Package):
            serializer = PackageSerializer
        else:
            serializer = BaseProductSerializer

        return serializer(instance=instance, context=self.context).data


class OrderLineBaseProductSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    class Meta:
        model = BaseProduct
        fields = ('id', 'quantity')

    def validate(self, attrs):
        product_id = attrs['id']
        quantity = attrs['quantity']
        base_product = BaseProduct.objects.get_subclass(id=product_id)
        if isinstance(base_product, OptionProduct):
            if quantity > base_product.max_quantity:
                raise serializers.ValidationError({
                    'quantity': [
                        f'Quantity too big, limited to '
                        f'{base_product.max_quantity}'
                    ]
                })

        return attrs


class BaseProductSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    price = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.1,
    )

    name = serializers.CharField(
        required=False,
        validators=[UniqueValidator(queryset=Retreat.objects.all())],
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Retreat.objects.all())],
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
        validators=[UniqueValidator(queryset=Retreat.objects.all())],
    )

    available = serializers.BooleanField(
        required=True
    )

    available_on_product_types = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model',
        many=True,
        required=False,
    )

    available_on_products = serializers.PrimaryKeyRelatedField(
        queryset=BaseProduct.objects.all(),
        many=True,
        required=False
    )

    def to_representation(self, instance):
        user = self.context['request'].user
        self.fields['options'] = BaseProductManagerSerializer(many=True)
        data = super(BaseProductSerializer, self).to_representation(instance)
        if not user.is_staff:
            data = remove_translation_fields(data)

        return data

    def run_validation(self, data=empty):

        def merge_err_dict(errs, new_errors):
            errs_copy = {**errs, **new_errors}
            for key, value in errs_copy.items():
                if key in errs and key in new_errors:
                    errs_copy[key] = value + errs[key]

            return errs_copy

        (is_empty_value, data) = self.validate_empty_values(data)
        if is_empty_value:
            return data

        errs = {}
        value = None
        try:
            value = self.to_internal_value(data)
        except (ValidationError, DjangoValidationError) as exc:
            errs = as_serializer_error(exc)

        try:
            self.run_validators(data)
        except (ValidationError, DjangoValidationError) as exc:
            errs = merge_err_dict(errs, as_serializer_error(exc))

        try:
            if value:
                value = self.validate(value)
            else:
                value = self.validate(data)
            assert value is not None, \
                '.validate() should return the validated data'
        except (ValidationError, DjangoValidationError) as exc:
            errs = merge_err_dict(errs, as_serializer_error(exc))

        if errs:
            raise serializers.ValidationError(errs)
        else:
            return value

    class Meta:
        model = BaseProduct
        fields = '__all__'
        abstract = True


class MembershipSerializer(BaseProductSerializer):

    def validate(self, attr):
        try:
            return super().validate(attr)
        except serializers.ValidationError as e:
            action = self.context['request'].parser_context['view'].action
            if action != 'partial_update':
                raise e
            return attr

    class Meta:
        model = Membership
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the membership."),
            },
        }


class PackageSerializer(BaseProductSerializer):
    reservations = serializers.IntegerField(
        min_value=1,
    )

    def validate(self, attr):
        try:
            return super().validate(attr)
        except serializers.ValidationError as e:
            action = self.context['request'].parser_context['view'].action
            if action != 'partial_update':
                raise e
            return attr

    class Meta:
        model = Package
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the package."),
            },
        }


class OptionProductSerializer(BaseProductSerializer):
    class Meta:
        model = OptionProduct
        fields = '__all__'


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
            amount = int(round(custom_payment.price * 100))

            # Charge the order with the external payment API
            try:
                charge_response = charge_payment(
                    amount,
                    single_use_token,
                    str(custom_payment.id)
                )
            except PaymentAPIError as err:
                raise serializers.ValidationError({
                    'non_field_errors': [err]
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

        Order.send_invoice([custom_payment.user.email], merge_data)

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
    coupon_real_value = serializers.ReadOnlyField()
    cost = serializers.ReadOnlyField()
    coupon = serializers.SlugRelatedField(
        slug_field='code',
        allow_null=True,
        required=False,
        read_only=True,
    )

    options = OrderLineBaseProductSerializer(
        many=True,
        required=False,
        write_only=True
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
                     or content_type.model == 'retreat')
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

        if (content_type.model == 'membership'
                or content_type.model == 'package'
                or content_type.model == 'retreat'):
            attrs['cost'] = obj.price * validated_data.get('quantity')

        return attrs

    class Meta:
        model = OrderLine
        fields = '__all__'

    def to_representation(self, instance: OrderLine):
        data = super(OrderLineSerializer, self).to_representation(instance)

        data['options'] = []
        options = instance.options.all()
        if options:
            option: BaseProduct
            for option in options:
                option_id = option.id
                option_quantity = option.orderlinebaseproduct_set.\
                    get(order_line_id=instance.id).quantity

                option_data = {
                    'id': option_id,
                    'quantity': option_quantity
                }
                data['options'].append(option_data)

        return data


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
        write_only=True,
    )

    target_user = serializers.HyperlinkedRelatedField(
        many=False,
        write_only=True,
        view_name='user-detail',
        required=False,
        allow_null=True,
        queryset=User.objects.all(),
    )

    bypass_payment = serializers.BooleanField(
        write_only=True,
        required=False,
    )

    # save_card = serializers.NullBooleanField(
    #     write_only=True,
    #     required=False,
    # )

    def create(self, validated_data):
        """
        Create an Order and charge the user.
        """
        user = self.context['request'].user
        is_staff = user.is_staff
        bypass_payment = False  # Default value
        if 'target_user' in validated_data.keys():
            if is_staff:
                user = validated_data.pop('target_user')
            else:
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                       "You don't have the permission to create "
                       "an order for another user."
                    )]
                })
        if 'bypass_payment' in validated_data.keys():
            if is_staff:
                bypass_payment = validated_data.pop('bypass_payment')
            else:
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "You don't have the permission to bypass the payment"
                    )]
                })

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

        retreat_reservations = list()

        if single_use_token and not profile:
            # Create external profile
            try:
                create_profile_response = create_external_payment_profile(
                    user
                )
            except PaymentAPIError as err:
                raise serializers.ValidationError({
                    'non_field_errors': [err]
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
            coupon = validated_data.pop('coupon', None)
            order = Order.objects.create(**validated_data)
            charge_response = None

            order.add_line_from_data(orderlines_data)

            discount_amount = 0
            if coupon:
                coupon_valid_use, error, discount_amount = \
                    order.applying_coupon(coupon, user)
                if not coupon_valid_use:
                    raise serializers.ValidationError(error)

            amount = order.total_cost_with_taxes
            tax = order.taxes

            membership_orderlines = order.order_lines.filter(
                content_type__model="membership"
            )
            package_orderlines = order.order_lines.filter(
                content_type__model="package"
            )
            reservation_orderlines = order.order_lines.filter(
                content_type__model="timeslot"
            )
            retreat_orderlines = order.order_lines.filter(
                content_type__model="retreat"
            )
            need_transaction = False

            if membership_orderlines:
                need_transaction = True
                # Allow to buy membership, 1 month before end of membership
                limit_date_to_renew = \
                    timezone.now().date() + relativedelta(months=1)
                if user.membership and user.membership_end > \
                        limit_date_to_renew:
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "You already have an active membership."
                        )]
                    })
                user.membership = membership_orderlines[0].content_object
                # If the user has already a membership end that
                # is after today,
                # we add the new membership duration to it
                today = timezone.now().date()
                if user.membership_end and user.membership_end > today:
                    user.membership_end = \
                        user.membership_end + user.membership.duration
                else:
                    user.membership_end = (
                            today + user.membership.duration
                    )
                user.save()

                membership_coupons = MembershipCoupon.objects.filter(
                    membership__pk=membership_orderlines[0].content_object.pk
                )

                for membership_coupon in membership_coupons:
                    coupon = Coupon.objects.create(
                        value=membership_coupon.value,
                        percent_off=membership_coupon.percent_off,
                        max_use=membership_coupon.max_use,
                        max_use_per_user=membership_coupon.max_use_per_user,
                        details=membership_coupon.details,
                        start_time=timezone.now(),
                        end_time=timezone.now() + membership_orderlines[
                            0].content_object.duration,
                        owner=user)
                    coupon.applicable_retreats.set(
                        membership_coupon.applicable_retreats.all())
                    coupon.applicable_timeslots.set(
                        membership_coupon.applicable_timeslots.all())
                    coupon.applicable_packages.set(
                        membership_coupon.applicable_packages.all())
                    coupon.applicable_memberships.set(
                        membership_coupon.applicable_memberships.all())
                    coupon.applicable_product_types.set(
                        membership_coupon.applicable_product_types.all())
                    coupon.generate_code()
                    coupon.save()

            if package_orderlines:
                need_transaction = True
                for package_orderline in package_orderlines:
                    user.tickets += (
                            package_orderline.content_object.reservations *
                            package_orderline.quantity
                    )
                    user.save()
            if reservation_orderlines:
                for reservation_orderline in reservation_orderlines:
                    timeslot = reservation_orderline.content_object
                    reservations = timeslot.reservations.filter(is_active=True)
                    reserved = reservations.count()
                    if timeslot.billing_price > user.tickets:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "You don't have enough tickets to make this "
                                "reservation."
                            )]
                        })
                    if reservations.filter(user=user):
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "You already are registered to this timeslot: "
                                "{0}.".format(str(timeslot))
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
                        if not bypass_payment:
                            user.tickets -= 1
                            user.save()
                    else:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "There are no places left in the requested "
                                "timeslot."
                            )]
                        })
            if retreat_orderlines:
                need_transaction = True
                if not (user.phone and user.city):
                    raise serializers.ValidationError({
                        'non_field_errors': [_(
                            "Incomplete user profile. 'phone' and 'city' "
                            "field must be filled in the user profile to book "
                            "a retreat."
                        )]
                    })

                for retreat_orderline in retreat_orderlines:
                    retreat = retreat_orderline.content_object
                    user_waiting = retreat.wait_queue.filter(user=user)
                    reservations = retreat.reservations.filter(
                        is_active=True
                    )
                    reserved = reservations.count()
                    if reservations.filter(user=user):
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "You already are registered to this "
                                "retreat: {0}.".format(str(retreat))
                            )]
                        })

                    invitation = retreat_orderline.get_invitation()
                    if ((retreat.has_places_remaining(invitation))
                            or (retreat.reserved_seats
                                and WaitQueueNotification.objects.filter(
                                        user=user, retreat=retreat))):

                        # Manage invitation to retreat
                        # The invitation id is store in the orderline metadata

                        new_retreat_reservation = \
                            RetreatReservation.objects.create(
                                user=user,
                                retreat=retreat,
                                order_line=retreat_orderline,
                                is_active=True
                            )

                        if invitation:
                            new_retreat_reservation.invitation = invitation
                            new_retreat_reservation.save()

                        retreat_reservations.append(
                            new_retreat_reservation
                        )

                        # Decrement reserved_seats if > 0
                        if retreat.reserved_seats:
                            retreat.reserved_seats = (
                                    retreat.reserved_seats - 1
                            )
                            retreat.save()
                    else:
                        raise serializers.ValidationError({
                            'non_field_errors': [_(
                                "There are no places left in the requested "
                                "retreat."
                            )]
                        })
                    if user_waiting:
                        user_waiting.delete()

            # Overwrite transaction depending on bypass_payment
            need_transaction = need_transaction and not bypass_payment
            if need_transaction and payment_token and int(amount):
                # Charge the order with the external payment API
                try:
                    charge_response = charge_payment(
                        int(round(amount)),
                        payment_token,
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'non_field_errors': [err]
                    })

            elif need_transaction and single_use_token and int(amount):
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
                        'non_field_errors': [err]
                    })
            elif (membership_orderlines
                  or package_orderlines
                  or retreat_orderlines) and int(amount):
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

        if need_transaction:
            # Send order email
            orderlines = order.order_lines.filter(
                models.Q(content_type__model='membership') |
                models.Q(content_type__model='package') |
                models.Q(content_type__model='retreat')
            )

            # Here, the 'details' key is used to provide details of the
            #  item to the email template.
            # As of now, only 'retreat' objects have the 'email_content'
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
                    # for retreats. Retreats instead have another
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
                'COST': round(amount / 100, 2),
            }

            Order.send_invoice([order.user.email], merge_data)

        # Send retreat informations emails
        for retreat_reservation in retreat_reservations:
            # Send info email
            merge_data = {
                'RETREAT': retreat_reservation.retreat,
                'USER': user,
            }
            if len(retreat_reservation.retreat.pictures.all()):
                merge_data['RETREAT_PICTURE'] = "{0}{1}".format(
                    settings.MEDIA_URL,
                    retreat_reservation.retreat.pictures.first().picture.url
                )

            plain_msg = render_to_string(
                "retreat_info.txt",
                merge_data
            )
            msg_html = render_to_string(
                "retreat_info.html",
                merge_data
            )

            try:
                send_mail(
                    "Confirmation d'inscription à la retraite",
                    plain_msg,
                    settings.DEFAULT_FROM_EMAIL,
                    [retreat_reservation.user.email],
                    html_message=msg_html,
                )
            except Exception as err:
                additional_data = {
                    'title': "Confirmation d'inscription à la retraite",
                    'default_from': settings.DEFAULT_FROM_EMAIL,
                    'user_email': retreat_reservation.user.email,
                    'merge_data': merge_data,
                    'template': 'retreat_info'
                }
                Log.error(
                    source='SENDING_BLUE_TEMPLATE',
                    message=err,
                    additional_data=json.dumps(additional_data)
                )
                raise

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
    code = serializers.CharField(
        allow_blank=True,
        required=False,
        validators=[
            UniqueValidator(queryset=Coupon.objects.all()),
        ]
    )
    value = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        min_value=0.0,
        required=False,
    )
    percent_off = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
    )
    max_use = serializers.IntegerField(
        min_value=0
    )
    max_use_per_user = serializers.IntegerField(
        min_value=0
    )

    def validate(self, attr):
        validated_data = super(CouponSerializer, self).validate(attr)
        if (validated_data.get('value', None) and
                validated_data.get('percent_off', None)):
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "You can't set a discount value (value) and a discount "
                    "percentage (percent_off) at the same time."
                )]
            })
        action = self.context['request'].parser_context['view'].action
        if action != 'partial_update':
            if (not validated_data.get('value', None) and
                    not validated_data.get('percent_off', None)):
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "You need to set a value discount (value) or a "
                        "discount percentage (percent_off) for this coupon."
                    )]
                })
        return validated_data

    def create(self, validated_data):
        """
        Generate coupon's code and create the coupon.
        """
        code = validated_data.get('code', None)

        used_code = Coupon.objects.all().values_list('code', flat=True)
        n = 0
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

    def update(self, instance, validated_data):

        new_value = validated_data.get('value', None)
        new_percent_off = validated_data.get('percent_off', None)

        value_off = (
                (not instance.value and new_value) or
                (instance.value and new_value != 0)
        )
        percent_off = (
                (not instance.percent_off and new_percent_off) or
                (instance.percent_off and new_percent_off != 0)
        )

        if value_off and percent_off:
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "You can't set a discount value (value) and a discount "
                    "percentage (percent_off) at the same time."
                )]
            })
        if not value_off and not percent_off:
            raise serializers.ValidationError({
                'non_field_errors': [_(
                    "You need to set a value discount (value) or a discount "
                    "percentage (percent_off) for this coupon."
                )]
            })

        return super(CouponSerializer, self).update(instance, validated_data)

    def to_representation(self, instance):
        data = super(CouponSerializer, self).to_representation(instance)
        from workplace.serializers import TimeSlotSerializer
        from retirement.serializers import RetreatSerializer
        action = self.context['view'].action
        if action == 'retrieve' or action == 'list':
            data['applicable_retreats'] = RetreatSerializer(
                instance.applicable_retreats,
                many=True,
                context={
                    'request': self.context['request'],
                    'view': self.context['view'],
                },
            ).data
            data['applicable_timeslots'] = TimeSlotSerializer(
                instance.applicable_timeslots,
                many=True,
                context={
                    'request': self.context['request'],
                    'view': self.context['view'],
                },
            ).data
            data['applicable_packages'] = PackageSerializer(
                instance.applicable_packages,
                many=True,
                context={
                    'request': self.context['request'],
                    'view': self.context['view'],
                },
            ).data
            data['applicable_memberships'] = MembershipSerializer(
                instance.applicable_memberships,
                many=True,
                context={
                    'request': self.context['request'],
                    'view': self.context['view'],
                },
            ).data
        return data

    class Meta:
        model = Coupon
        exclude = ('deleted',)
        extra_kwargs = {
            'applicable_retreats': {
                'required': False,
                'view_name': 'retreat:retreat-detail',
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


class CouponUserSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = CouponUser
        exclude = ('deleted',)


class RefundSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Refund
        exclude = ('deleted',)
