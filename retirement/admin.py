from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from safedelete.admin import SafeDeleteAdmin, highlight_deleted
from simple_history.admin import SimpleHistoryAdmin

from .models import (Picture, Reservation, Retirement, WaitQueue,
                     WaitQueueNotification, )
from .resources import (ReservationResource, RetirementResource,
                        WaitQueueResource)


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag', )


class RetirementAdmin(SimpleHistoryAdmin, SafeDeleteAdmin, TranslationAdmin,
                      ExportActionModelAdmin):
    resource_class = RetirementResource
    inlines = (PictureAdminInline, )
    list_display = (
        'name',
        'seats',
        'start_time',
        'end_time',
        'price',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        'name',
        'seats',
        'start_time',
        'end_time',
        'price',
    ) + SafeDeleteAdmin.list_filter


class PictureAdmin(SimpleHistoryAdmin, TranslationAdmin):
    list_display = (
        'name',
        'retirement',
        'picture_tag',
    )


class ReservationAdmin(SimpleHistoryAdmin, SafeDeleteAdmin,
                       ExportActionModelAdmin):
    resource_class = ReservationResource
    list_display = (
        'user',
        'retirement',
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        ('retirement', admin.RelatedOnlyFieldListFilter),
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
    ) + SafeDeleteAdmin.list_filter


class WaitQueueAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = WaitQueueResource
    list_display = (
        'user',
        'retirement',
        'created_at',
    )
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        ('retirement', admin.RelatedOnlyFieldListFilter),
        'created_at',
    )


class WaitQueueNotificationAdmin(SimpleHistoryAdmin):
    list_display = (
        'retirement',
        'user',
        'created_at',
    )
    list_filter = (
        ('retirement', admin.RelatedOnlyFieldListFilter),
        ('user', admin.RelatedOnlyFieldListFilter),
        'created_at',
    )


admin.site.register(Retirement, RetirementAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(WaitQueue, WaitQueueAdmin)
admin.site.register(WaitQueueNotification, WaitQueueNotificationAdmin)
