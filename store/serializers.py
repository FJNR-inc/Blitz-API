from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import (Package, Membership, Order, OrderLine, BaseProduct,
                     CreditCard)


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


class CreditCardSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = CreditCard
        fields = '__all__'
        extra_kwargs = {
            'name': {
                'help_text': _("Name of the credit card."),
                'validators': [
                    UniqueValidator(queryset=CreditCard.objects.all())
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

        return attrs

    class Meta:
        model = OrderLine
        fields = '__all__'


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    authorization_id = serializers.ReadOnlyField()
    settlement_id = serializers.ReadOnlyField()
    order_lines = OrderLineSerializer(many=True)
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

    @transaction.atomic()
    def create(self, validated_data):
        orderlines_data = validated_data.pop('order_lines')
        payment_token = validated_data.pop('payment_token', None)
        single_use_token = validated_data.pop('single_use_token', None)
        validated_data['authorization_id'] = "1"
        validated_data['settlement_id'] = "1"
        order = Order.objects.create(**validated_data)
        for orderline_data in orderlines_data:
            orderline_data.pop('order')
            OrderLine.objects.create(order=order, **orderline_data)

        if payment_token:
            # Validate the payment with Paysafe
            pass
        elif single_use_token:
            # Validate the payment with Paysafe
            pass
        else:
            pass
            # return serializers.ValidationError({
            #     "non_field_errors": [_(
            #         "A payment_token or single_use_token is required to "
            #         "create an order."
            #     )]
            # })

        user = order.user
        membership_orderlines = order.order_lines.filter(
            content_type__model="membership"
        )
        package_orderlines = order.order_lines.filter(
            content_type__model="package"
        )
        if membership_orderlines:
            user.membership = membership_orderlines[0].content_object
        if package_orderlines:
            for package_orderline in package_orderlines:
                # new_tickets = sum(
                #    packages_order.values_list(
                #        "content_object__tickets", flat=True
                #    )
                # )
                # user.tickets += new_tickets
                user.tickets += (
                    package_orderline.content_object.reservations *
                    package_orderline.quantity
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
