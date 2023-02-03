from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from safedelete.admin import SafeDeleteAdmin, highlight_deleted
from simple_history.admin import SimpleHistoryAdmin

from blitz_api.admin import UserFilter
from .models import Period, Picture, Reservation, TimeSlot, Workplace
from .resources import (PeriodResource, ReservationResource, TimeSlotResource,
                        WorkplaceResource)


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag',)


class WorkplaceAdmin(SimpleHistoryAdmin, SafeDeleteAdmin, TranslationAdmin,
                     ExportActionModelAdmin):
    resource_class = WorkplaceResource
    inlines = (PictureAdminInline,)
    list_display = (
        'name',
        'seats',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        'name',
        'seats',
    ) + SafeDeleteAdmin.list_filter

    actions = ['undelete_selected', 'export_admin_action']


class PictureAdmin(SimpleHistoryAdmin, TranslationAdmin):
    list_display = ('name', 'workplace', 'picture_tag',)


class PeriodAdmin(SimpleHistoryAdmin, SafeDeleteAdmin, TranslationAdmin,
                  ExportActionModelAdmin):
    resource_class = PeriodResource
    list_display = (
        'name',
        'workplace',
        'price',
        'start_date',
        'end_date',
        'is_active',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        'name',
        ('workplace', admin.RelatedOnlyFieldListFilter),
        'price',
        'start_date',
        'end_date',
        'is_active',
    ) + SafeDeleteAdmin.list_filter

    actions = ['undelete_selected', 'export_admin_action']


class TimeSlotAdmin(SimpleHistoryAdmin, SafeDeleteAdmin,
                    ExportActionModelAdmin):
    resource_class = TimeSlotResource
    list_display = (
        'start_time',
        'end_time',
        'period',
        'price',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        'start_time',
        'end_time',
        ('period', admin.RelatedOnlyFieldListFilter),
        ('period__workplace', admin.RelatedOnlyFieldListFilter),
        'price',
    ) + SafeDeleteAdmin.list_filter

    actions = ['undelete_selected', 'export_admin_action']

    search_fields = (
        'period__name',
        'period__workplace__name',
    )


class TimeSlotFilter(AutocompleteFilter):
    title = 'Time Slot'
    field_name = 'timeslot'


class ReservationAdmin(SimpleHistoryAdmin, SafeDeleteAdmin,
                       ExportActionModelAdmin):
    resource_class = ReservationResource
    list_display = (
        'user',
        'timeslot',
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        UserFilter,
        TimeSlotFilter,
        ('timeslot__period', admin.RelatedOnlyFieldListFilter),
        ('timeslot__period__workplace', admin.RelatedOnlyFieldListFilter),
        'is_active',
        'cancelation_date',
        'cancelation_reason',
    ) + SafeDeleteAdmin.list_filter

    actions = ['undelete_selected', 'export_admin_action']

    search_fields = (
        'user__email',
        'user__username',
    )
    autocomplete_fields = ('user', 'timeslot')

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


admin.site.register(Workplace, WorkplaceAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(Reservation, ReservationAdmin)
