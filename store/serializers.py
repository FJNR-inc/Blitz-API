from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from .models import Package, Membership, Order, OrderLine


class BaseProductSerializer(serializers.HyperlinkedModelSerializer):

    order_lines = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='orderline-detail'
    )

    def to_representation(self, instance):
        user = self.context['request'].user
        data = super(BaseProductSerializer, self).to_representation(instance)
        if not user.is_staff:
            data.pop("order_lines")
        return data

    class Meta:
        model = Membership
        fields = '__all__'
        abstract = True


class MembershipSerializer(BaseProductSerializer):
    id = serializers.ReadOnlyField()

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
    id = serializers.ReadOnlyField()

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

    class Meta:
        model = OrderLine
        fields = '__all__'
