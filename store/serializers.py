from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from .models import Package, Membership, Order, OrderLine, BaseProduct


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


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = '__all__'


class OrderLineSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model',
    )

    def validate(self, attrs):
        """Limits packages according to request membership"""
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
        obj = content_type.get_object_for_this_type(pk=object_id)

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
