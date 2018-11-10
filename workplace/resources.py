from django.apps import apps
from django.contrib.auth import get_user_model

from import_export import fields, resources
from import_export.widgets import (ForeignKeyWidget, ManyToManyWidget,
                                   DateTimeWidget)

from .models import Period, Reservation, TimeSlot, Workplace


User = get_user_model()


# django-import-export models declaration
# These represent the models data that will be importd/exported
class PeriodResource(resources.ModelResource):

    workplace = fields.Field(
        column_name='workplace',
        attribute='workplace',
        widget=ForeignKeyWidget(Workplace, 'name'),
    )

    class Meta:
        model = Period
        fields = (
            'id',
            'name',
            'workplace',
            'start_date',
            'end_date',
            'price',
            'is_active',
        )
        export_order = (
            'id',
            'name',
            'workplace',
            'start_date',
            'end_date',
            'price',
            'is_active',
        )


class ReservationResource(resources.ModelResource):

    user = fields.Field(
        column_name='user',
        attribute='user',
        widget=ForeignKeyWidget(User, 'email'),
    )

    cancelation_reason = fields.Field(
        column_name='cancelation_reason',
        attribute='get_cancelation_reason_display',
    )

    start_time = fields.Field(
        column_name='start_time',
        attribute='timeslot__start_time',
        widget=DateTimeWidget(),
    )

    end_time = fields.Field(
        column_name='end_time',
        attribute='timeslot__end_time',
        widget=DateTimeWidget(),
    )

    class Meta:
        model = Reservation
        fields = (
            'id',
            'user',
            'timeslot',
            'start_time',
            'end_time',
            'cancelation_date',
            'cancelation_reason',
            'is_active',
        )
        export_order = (
            'id',
            'user',
            'timeslot',
            'start_time',
            'end_time',
            'cancelation_date',
            'cancelation_reason',
            'is_active',
        )


class TimeSlotResource(resources.ModelResource):

    period = fields.Field(
        column_name='period',
        attribute='period',
        widget=ForeignKeyWidget(Period, 'name'),
    )

    class Meta:
        model = TimeSlot
        fields = (
            'id',
            'start_time',
            'end_time',
            'price',
            'period',
        )
        export_order = (
            'id',
            'start_time',
            'end_time',
            'price',
            'period',
        )


class WorkplaceResource(resources.ModelResource):

    class Meta:
        model = Workplace
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
        )
