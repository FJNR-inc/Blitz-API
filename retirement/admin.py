from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from safedelete.admin import SafeDeleteAdmin, highlight_deleted
from simple_history.admin import SimpleHistoryAdmin

from .models import (Picture, Reservation, Retreat, WaitQueue,
                     RetreatInvitation, WaitQueuePlace, WaitQueuePlaceReserved)
from .resources import (ReservationResource, RetreatResource,
                        WaitQueueResource)


class PictureAdminInline(admin.TabularInline):
    model = Picture
    show_change_link = True
    readonly_fields = ('picture_tag', )


class RetreatAdmin(SimpleHistoryAdmin,
                   ExportActionModelAdmin,
                   SafeDeleteAdmin,
                   TranslationAdmin):
    resource_class = RetreatResource
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

    search_fields = [
        'name_fr',
        'name_en',
        'id'
    ]

    actions = ['undelete_selected', 'export_admin_action']


class PictureAdmin(SimpleHistoryAdmin, TranslationAdmin):
    list_display = (
        'name',
        'retreat',
        'picture_tag',
    )


class ReservationAdmin(SimpleHistoryAdmin,
                       ExportActionModelAdmin,
                       SafeDeleteAdmin):
    resource_class = ReservationResource
    list_display = (
        'user',
        'retreat',
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        ('retreat', admin.RelatedOnlyFieldListFilter),
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
    ) + SafeDeleteAdmin.list_filter

    autocomplete_fields = ['user', 'order_line', 'retreat', 'invitation']

    actions = ['undelete_selected', 'export_admin_action']


class WaitQueueAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = WaitQueueResource
    list_display = (
        'user',
        'retreat',
        'created_at',
    )
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        ('retreat', admin.RelatedOnlyFieldListFilter),
        'created_at',
    )


class ReservationAdminInline(admin.TabularInline):
    model = Reservation

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


class RetreatInvitationAdmin(SimpleHistoryAdmin,
                             SafeDeleteAdmin):
    inlines = (ReservationAdminInline,)
    list_display = (
        'name',
        'coupon',
        'retreat',
        'nb_places',
        highlight_deleted,
    ) + SafeDeleteAdmin.list_display

    list_filter = (
        ('retreat', admin.RelatedOnlyFieldListFilter),
        ('coupon', admin.RelatedOnlyFieldListFilter)
    ) + SafeDeleteAdmin.list_filter

    search_fields = (
        'name', 'id',
    )


class WaitQueuePlaceReservedInline(admin.StackedInline):
    model = WaitQueuePlaceReserved
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Wait Queue places reserved')


class WaitQueuePlaceAdmin(admin.ModelAdmin):
    inlines = (WaitQueuePlaceReservedInline,)
    list_display = (
        'id',
        'retreat',
        'create',
        'available'
    )
    list_filter = (
        'retreat',
        'cancel_by'
    )
    autocomplete_fields = ('cancel_by', 'retreat')
    search_fields = ('retreat', 'id')


class WaitQueuePlaceReservedAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'wait_queue_place',
        'user',
        'create',
        'notified'
    )
    list_filter = (
        'wait_queue_place',
        'user'
    )
    autocomplete_fields = ('user', 'wait_queue_place')


admin.site.register(Retreat, RetreatAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(WaitQueue, WaitQueueAdmin)
admin.site.register(RetreatInvitation, RetreatInvitationAdmin)
admin.site.register(WaitQueuePlace, WaitQueuePlaceAdmin)
admin.site.register(WaitQueuePlaceReserved, WaitQueuePlaceReservedAdmin)
