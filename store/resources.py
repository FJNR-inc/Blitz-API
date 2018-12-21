from django.apps import apps
from django.contrib.auth import get_user_model

from import_export import fields, resources
from import_export.widgets import (ForeignKeyWidget, ManyToManyWidget,
                                   DateTimeWidget)

from blitz_api.models import AcademicLevel
from blitz_api.services import get_model_from_name

from .models import Membership, Order, OrderLine, Package, CustomPayment


User = get_user_model()


# django-import-export models declaration
# These represent the models data that will be importd/exported
class MembershipResource(resources.ModelResource):

    academic_levels = fields.Field(
        column_name='academic_levels',
        attribute='academic_levels',
        widget=ManyToManyWidget(AcademicLevel, ',', 'name'),
    )

    class Meta:
        model = Membership
        fields = (
            'id',
            'name',
            'details',
            'price',
            'duration',
            'academic_levels',
            'available',
        )
        export_order = (
            'id',
            'name',
            'details',
            'price',
            'duration',
            'academic_levels',
            'available',
        )


class OrderResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    class Meta:
        model = Order
        fields = (
            'id',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
        )
        export_order = (
            'id',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
        )


class OrderLineResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='order__user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    item_type = fields.Field(
        column_name='item_type',
        attribute='content_type__model',
    )

    item_name = fields.Field()

    item_id = fields.Field()

    def dehydrate_item_name(self, orderline):
        model = get_model_from_name(orderline.content_type.model)
        return model.objects.get(id=orderline.object_id).name

    def dehydrate_item_id(self, orderline):
        model = get_model_from_name(orderline.content_type.model)
        return model.objects.get(id=orderline.object_id).id

    class Meta:
        model = OrderLine
        fields = (
            'id',
            'user',
            'item_type',
            'item_name',
            'item_id',
            'quantity',
            'order',
        )
        export_order = (
            'id',
            'user',
            'item_type',
            'item_name',
            'item_id',
            'quantity',
            'order',
        )


class PackageResource(resources.ModelResource):

    memberships = fields.Field(
        column_name='memberships',
        attribute='exclusive_memberships',
        widget=ManyToManyWidget(Membership, ',', 'name'),
    )

    class Meta:
        model = Package
        fields = (
            'id',
            'name',
            'details',
            'price',
            'reservations',
            'memberships',
            'available',
        )
        export_order = (
            'id',
            'name',
            'details',
            'price',
            'reservations',
            'memberships',
            'available',
        )


class CustomPaymentResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    class Meta:
        model = CustomPayment
        fields = (
            'id',
            'name',
            'details',
            'price',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
        )
        export_order = (
            'id',
            'name',
            'details',
            'price',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
        )


class CouponResource(resources.ModelResource):

    owner = fields.Field(
        column_name='owner',
        attribute='owner',
        widget=ForeignKeyWidget(User, 'email'),
    )

    class Meta:
        model = CustomPayment
        fields = (
            'id',
            'details',
            'value',
            'code',
            'owner',
            'start_time',
            'end_time',
        )
        export_order = (
            'id',
            'details',
            'value',
            'code',
            'owner',
            'start_time',
            'end_time',
        )
