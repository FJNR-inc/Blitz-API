from django.apps import apps
from django.contrib.auth import get_user_model

from import_export import fields, resources
from import_export.widgets import (ForeignKeyWidget, ManyToManyWidget,
                                   DateTimeWidget)

from blitz_api.models import AcademicLevel
from blitz_api.services import get_model_from_name

from .models import (Membership, Order, OrderLine, Package, CustomPayment,
                     Coupon, CouponUser, Refund, )


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

    coupon = fields.Field(
        column_name='coupon',
        attribute='coupon',
        widget=ForeignKeyWidget(Coupon, 'code'),
    )

    class Meta:
        model = Order
        fields = (
            'id',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
            'coupon',
        )
        export_order = (
            'id',
            'user',
            'transaction_date',
            'authorization_id',
            'settlement_id',
            'coupon',
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

    total_use = fields.Field()

    def dehydrate_total_use(self, coupon):
        uses = CouponUser.objects.filter(coupon=coupon)
        return sum(uses.values_list('uses', flat=True))

    class Meta:
        model = Coupon
        fields = (
            'id',
            'details',
            'value',
            'percent_off',
            'code',
            'owner',
            'start_time',
            'end_time',
            'total_use',
        )
        export_order = (
            'id',
            'details',
            'value',
            'percent_off',
            'code',
            'owner',
            'start_time',
            'end_time',
            'total_use',
        )


class CouponUserResource(resources.ModelResource):

    user_email = fields.Field(
        column_name='user_email',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    user_firstname = fields.Field(
        column_name='user_firstname',
        attribute='user',
        widget=ForeignKeyWidget(User, 'first_name'),
    )

    user_lastname = fields.Field(
        column_name='user_lastname',
        attribute='user',
        widget=ForeignKeyWidget(User, 'last_name'),
    )

    student_number = fields.Field(
        column_name='student_number',
        attribute='user',
        widget=ForeignKeyWidget(User, 'student_number'),
    )

    academic_program_code = fields.Field(
        column_name='academic_program_code',
        attribute='user',
        widget=ForeignKeyWidget(User, 'academic_program_code'),
    )

    class Meta:
        model = CouponUser
        fields = (
            'user_email',
            'user_firstname',
            'user_lastname',
            'student_number',
            'academic_program_code',
            'uses',
        )
        export_order = (
            'user_email',
            'user_firstname',
            'user_lastname',
            'student_number',
            'academic_program_code',
            'uses',
        )


class RefundResource(resources.ModelResource):

    orderline = fields.Field(
        column_name='orderline',
        attribute='orderline',
        widget=ForeignKeyWidget(OrderLine, 'content_type__model'),
    )

    product_name = fields.Field(
        column_name='product_name',
        attribute='orderline',
        widget=ForeignKeyWidget(OrderLine, 'content_object__name'),
    )

    class Meta:
        model = Refund
        fields = (
            'id',
            'orderline',
            'product_name',
            'amount',
            'details',
            'refund_date',
        )
        export_order = (
            'id',
            'orderline',
            'product_name',
            'amount',
            'details',
            'refund_date',
        )
