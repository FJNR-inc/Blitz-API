from django.apps import apps
from django.contrib.auth import get_user_model

from import_export import fields, resources
from import_export.widgets import (ForeignKeyWidget, ManyToManyWidget,
                                   DateTimeWidget)

from store.models import OrderLine
from .models import Reservation, Retreat

User = get_user_model()


# django-import-export models declaration
# These represent the models data that will be importd/exported
class ReservationResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    retreat = fields.Field(
        column_name='retreat',
        attribute='retreat',
        widget=ForeignKeyWidget(Retreat, 'name'),
    )

    cancelation_reason = fields.Field(
        column_name='cancelation_reason',
        attribute='get_cancelation_reason_display',
    )

    cancelation_action = fields.Field(
        column_name='cancelation_action',
        attribute='get_cancelation_action_display',
    )

    start_time = fields.Field(
        column_name='start_time',
        attribute='retreat__start_time',
        widget=DateTimeWidget(),
    )

    end_time = fields.Field(
        column_name='end_time',
        attribute='retreat__end_time',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Reservation
        fields = (
            'id',
            'user',
            'retreat',
            'start_time',
            'end_time',
            'cancelation_date',
            'cancelation_reason',
            'cancelation_action',
            'is_active',
            'is_present',
        )
        export_order = (
            'id',
            'user',
            'retreat',
            'start_time',
            'end_time',
            'cancelation_date',
            'cancelation_reason',
            'cancelation_action',
            'is_active',
            'is_present',
        )


class RetreatResource(resources.ModelResource):
    class Meta:
        model = Retreat
        fields = (
            'id',
            'name',
            'details',
            'seats',
            'address_line1',
            'city',
            'state_province',
            'country',
            'postal_code',
            'price',
            'min_day_refund',
            'min_day_exchange',
            'refund_rate',
        )
        export_order = (
            'id',
            'name',
            'details',
            'seats',
            'address_line1',
            'city',
            'state_province',
            'country',
            'postal_code',
            'price',
            'min_day_refund',
            'min_day_exchange',
            'refund_rate',
        )


class WaitQueueResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    retreat = fields.Field(
        column_name='retreat',
        attribute='retreat',
        widget=ForeignKeyWidget(Retreat, 'name'),
    )

    created_at = fields.Field(
        column_name='created_at',
        attribute='created_at',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Retreat
        fields = (
            'id',
            'user',
            'retreat',
            'created_at',
        )
        export_order = (
            'id',
            'user',
            'retreat',
            'created_at',
        )


class WaitQueueNotificationResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    retreat = fields.Field(
        column_name='retreat',
        attribute='retreat',
        widget=ForeignKeyWidget(Retreat, 'name'),
    )

    created_at = fields.Field(
        column_name='created_at',
        attribute='created_at',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Retreat
        fields = (
            'id',
            'user',
            'retreat',
            'created_at',
        )
        export_order = (
            'id',
            'user',
            'retreat',
            'created_at',
        )


class RetreatReservationResource(resources.ModelResource):
    last_name = fields.Field(
        column_name='last_name',
        attribute='user',
        widget=ForeignKeyWidget(User, 'last_name'),
    )

    first_name = fields.Field(
        column_name='first_name',
        attribute='user',
        widget=ForeignKeyWidget(User, 'first_name'),
    )

    email = fields.Field(
        column_name='email',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    status = fields.Field(
        column_name='status',
        attribute='user',
        widget=ForeignKeyWidget(User, 'membership__name'),
    )

    order_date = fields.Field(
        column_name='order_date',
        attribute='order_line__order__transaction_date',
        widget=DateTimeWidget(),
    )

    promo_code = fields.Field(
        column_name='promo_code',
        attribute='order_line',
        widget=ForeignKeyWidget(OrderLine, 'coupon__code'),
    )

    personnal_restrictions = fields.Field(
        column_name='personnal_restriction',
        attribute='user',
        widget=ForeignKeyWidget(User, 'personnal_restrictions'),
    )

    city = fields.Field(
        column_name='city',
        attribute='user',
        widget=ForeignKeyWidget(User, 'city'),
    )

    phone = fields.Field(
        column_name='phone',
        attribute='user',
        widget=ForeignKeyWidget(User, 'phone'),
    )

    class Meta:
        model = Reservation
        fields = (
            'last_name',
            'first_name',
            'email',
            'status',
            'order_date',
            'promo_code',
            'personnal_restrictions',
            'city',
            'phone'
        )
        export_order = (
            'last_name',
            'first_name',
            'email',
            'status',
            'order_date',
            'promo_code',
            'personnal_restrictions',
            'city',
            'phone'
        )
