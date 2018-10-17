from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from safedelete.admin import SafeDeleteAdmin, highlight_deleted

from simple_history.admin import SimpleHistoryAdmin

from .models import Workplace, Picture, Period, TimeSlot, Reservation


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag',)


class WorkplaceAdmin(SimpleHistoryAdmin, SafeDeleteAdmin):
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


class PictureAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'workplace', 'picture_tag',)


class PeriodAdmin(SimpleHistoryAdmin, SafeDeleteAdmin):
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


class TimeSlotAdmin(SimpleHistoryAdmin, SafeDeleteAdmin):
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


class ReservationAdmin(SimpleHistoryAdmin, SafeDeleteAdmin):
    list_display = (
        'user',
        'timeslot',
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        ('timeslot', admin.RelatedOnlyFieldListFilter),
        ('timeslot__period', admin.RelatedOnlyFieldListFilter),
        ('timeslot__period__workplace', admin.RelatedOnlyFieldListFilter),
        'is_active',
        'cancelation_date',
        'cancelation_reason',
    ) + SafeDeleteAdmin.list_filter


admin.site.register(Workplace, WorkplaceAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(Reservation, ReservationAdmin)
