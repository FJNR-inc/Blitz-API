from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from simple_history.admin import SimpleHistoryAdmin

from .models import Workplace, Picture, Period, TimeSlot, Reservation


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag',)


class WorkplaceAdmin(SimpleHistoryAdmin):
    inlines = (PictureAdminInline,)


class PictureAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'workplace', 'picture_tag',)


class PeriodAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'workplace',
        'price',
        'start_date',
        'end_date',
        'is_active',
    )


class TimeSlotAdmin(SimpleHistoryAdmin):
    list_display = (
        'start_time',
        'end_time',
        'period',
        'price',
    )


class ReservationAdmin(SimpleHistoryAdmin):
    list_display = (
        'user',
        'timeslot',
        'is_active',
    )


admin.site.register(Workplace, WorkplaceAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
admin.site.register(Reservation, ReservationAdmin)
