from rest_framework import serializers
from rest_framework.validators import UniqueValidator

import decimal

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, models
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from workplace.models import Reservation

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, BaseProduct,
                     PaymentProfile,)
from .services import (charge_payment,
                       create_external_payment_profile,
                       create_external_card,
                       get_external_cards,
                       PAYSAFE_CARD_TYPE,)


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

    def to_representation(self, instance):
        user = self.context['request'].user
        data = super(BaseProductSerializer, self).to_representation(instance)
        if not user.is_staff:
            data.pop("order_lines")
        return data

    class Meta:
        model = BaseProduct
        fields = '__all__'
        abstract = True


class MembershipSerializer(BaseProductSerializer):
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

        user_membership = self.context['request'].user.membership
        user_academic_level = self.context['request'].user.academic_level

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

        if (not self.context['request'].user.is_staff and
                content_type.model == 'package' and
                obj.exclusive_memberships.all() and
                user_membership not in obj.exclusive_memberships.all()):
            raise serializers.ValidationError({
                'object_id': [
                    _(
                        "User does not have the required membership to order "
                        "this package."
                    )
                ],
            })
        if (not self.context['request'].user.is_staff and
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
        allow_blank=True
    )

    def create(self, validated_data):
        """
        Create an Order and charge the user.
        """
        user = self.context['request'].user
        orderlines_data = validated_data.pop('order_lines')
        payment_token = validated_data.pop('payment_token', None)
        single_use_token = validated_data.pop('single_use_token', None)
        # Temporary IDs until the external profile is created.
        validated_data['authorization_id'] = "0"
        validated_data['settlement_id'] = "0"
        validated_data['transaction_date'] = timezone.now()
        validated_data['user'] = user
        profile = PaymentProfile.objects.filter(owner=user).first()

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
            for orderline_data in orderlines_data:
                OrderLine.objects.create(order=order, **orderline_data)
            amount = int(round(order.total_cost*100))

            membership_orderlines = order.order_lines.filter(
                content_type__model="membership"
            )
            package_orderlines = order.order_lines.filter(
                content_type__model="package"
            )
            reservation_orderlines = order.order_lines.filter(
                content_type__model="timeslot"
            )

            if membership_orderlines:
                user.membership = membership_orderlines[0].content_object
                user.membership_end = (
                    timezone.now() + user.membership.duration
                )
            if package_orderlines:
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

            if payment_token:
                # Charge the order with the external payment API
                try:
                    charge_response = charge_payment(
                        amount,
                        payment_token,
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })

            elif single_use_token:
                # Add card to the external profile & charge user
                try:
                    card_create_response = create_external_card(
                        profile.external_api_id,
                        single_use_token
                    )
                    charge_response = charge_payment(
                        amount,
                        card_create_response.json()['paymentToken'],
                        str(order.id)
                    )
                except PaymentAPIError as err:
                    raise serializers.ValidationError({
                        'message': err
                    })
            else:
                raise serializers.ValidationError({
                    'non_field_errors': [_(
                        "A payment_token or single_use_token is required to "
                        "create an order."
                    )]
                })

            charge_res_content = charge_response.json()
            order.authorization_id = charge_res_content['id']
            order.settlement_id = charge_res_content['settlements'][0]['id']
            order.save()

            user.save()

            TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']

            orderlines = order.order_lines.filter(
                models.Q(content_type__model='membership') |
                models.Q(content_type__model='package')
            )

            items = [
                {
                    'price': orderline.content_object.price,
                    'name': "{0}: {1}".format(
                        str(orderline.content_type),
                        orderline.content_object.name
                    )
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
                'AUTHORIZATION': order.authorization_id,
                'TYPE': "Achat",
                'SELLER_COORDINATES': "",
                'ITEM_LIST': items,
                'TAX': round(decimal.Decimal(float(
                    sum(item['price'] for item in items)
                ) * TAX_RATE), 2),
                'COST': order.total_cost,
            }

            plain_msg = render_to_string("invoice.txt", merge_data)
            msg_html = render_to_string("invoice.html", merge_data)

            send_mail(
                'Thèsez-Vous?: Reçu pour votre achat',
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [order.user.email],
                html_message=msg_html,
            )

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
