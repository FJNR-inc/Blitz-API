from django.apps import apps
from django.contrib.auth import get_user_model

from import_export import fields, resources
from import_export.widgets import (ForeignKeyWidget, ManyToManyWidget,
                                   DateTimeWidget)

from .models import Reservation, Retirement

User = get_user_model()


# django-import-export models declaration
# These represent the models data that will be importd/exported
class ReservationResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    retirement = fields.Field(
        column_name='retirement',
        attribute='retirement',
        widget=ForeignKeyWidget(Retirement, 'name'),
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
        attribute='retirement__start_time',
        widget=DateTimeWidget(),
    )

    end_time = fields.Field(
        column_name='end_time',
        attribute='retirement__end_time',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Reservation
        fields = (
            'id',
            'user',
            'retirement',
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
            'retirement',
            'start_time',
            'end_time',
            'cancelation_date',
            'cancelation_reason',
            'cancelation_action',
            'is_active',
            'is_present',
        )


class RetirementResource(resources.ModelResource):
    class Meta:
        model = Retirement
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

    retirement = fields.Field(
        column_name='retirement',
        attribute='retirement',
        widget=ForeignKeyWidget(Retirement, 'name'),
    )

    created_at = fields.Field(
        column_name='created_at',
        attribute='created_at',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Retirement
        fields = (
            'id',
            'user',
            'retirement',
            'created_at',
        )
        export_order = (
            'id',
            'user',
            'retirement',
            'created_at',
        )


class WaitQueueNotificationResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    retirement = fields.Field(
        column_name='retirement',
        attribute='retirement',
        widget=ForeignKeyWidget(Retirement, 'name'),
    )

    created_at = fields.Field(
        column_name='created_at',
        attribute='created_at',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Retirement
        fields = (
            'id',
            'user',
            'retirement',
            'created_at',
        )
        export_order = (
            'id',
            'user',
            'retirement',
            'created_at',
        )
