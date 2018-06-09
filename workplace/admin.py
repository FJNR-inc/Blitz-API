from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Workplace, Picture, Period, TimeSlot


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag',)


class WorkplaceAdmin(admin.ModelAdmin):
    inlines = (PictureAdminInline,)


class PictureAdmin(admin.ModelAdmin):
    list_display = ('name', 'workplace', 'picture_tag',)


class PeriodAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'workplace',
        'price',
        'start_date',
        'end_date',
        'is_active',
    )


class TimeSlotAdmin(admin.ModelAdmin):
    list_display = (
        'start_time',
        'end_time',
        'period',
        'price',
    )


admin.site.register(Workplace, WorkplaceAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Period, PeriodAdmin)
admin.site.register(TimeSlot, TimeSlotAdmin)
