from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from safedelete.admin import (
    SafeDeleteAdmin,
    highlight_deleted,
)
from simple_history.admin import SimpleHistoryAdmin

from blitz_api.admin import UserFilter
from store.admin import CouponFilter
from .models import (
    Picture,
    Reservation,
    Retreat,
    WaitQueue,
    RetreatInvitation,
    WaitQueuePlace,
    WaitQueuePlaceReserved,
    RetreatType,
    AutomaticEmail,
    AutomaticEmailLog,
    RetreatDate,
    RetreatUsageLog,
)
from .resources import (
    ReservationResource,
    RetreatResource,
    WaitQueueResource
)

from .exports import (
    generate_retreat_sales,
    generate_retreat_participation
)

User = get_user_model()


class RetreatFilter(AutocompleteFilter):
    title = 'Retreat'
    field_name = 'retreat'


class CancelByFilter(AutocompleteFilter):
    title = 'Cancel by'
    field_name = 'cancel_by'


class WaitQueuePlaceFilter(AutocompleteFilter):
    title = 'Wait Queue Place'
    field_name = 'wait_queue_place'


class PictureAdminInline(admin.TabularInline):
    model = Picture
    show_change_link = True
    readonly_fields = ('picture_tag', )


class ReservationUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    rel_model = Reservation

    @property
    def parameter_name(self):
        return "reservation__user"

    @parameter_name.setter
    def parameter_name(self, value):
        pass


class ReservationRetreatFilter(AutocompleteFilter):
    title = 'Retreat'
    field_name = 'retreat'
    rel_model = Reservation

    @property
    def parameter_name(self):
        return "reservation__retreat"

    @parameter_name.setter
    def parameter_name(self, value):
        pass


def make_reservation_refundable(self, request, queryset):

    Reservation.objects.filter(
        retreat__in=queryset
    ).update(refundable=True)


make_reservation_refundable.\
    short_description = 'Make reservation refundable'


def make_reservation_not_refundable(self, request, queryset):

    Reservation.objects.filter(
        retreat__in=queryset
    ).update(refundable=False)


make_reservation_not_refundable.\
    short_description = 'Make reservation not refundable'


def export_retreat_sales(self, request, queryset):
    new_export = generate_retreat_sales(queryset)

    with new_export.file.open('r') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=%s' % \
                                          f.name.split('/')[-1:][0]
    return response


export_retreat_sales.short_description = 'export_retreat_sales'


def export_retreat_participation(self, request, queryset):
    for retreat in queryset:
        generate_retreat_participation.delay(request.user.id, retreat.id)


export_retreat_participation.short_description = \
    'export_retreat_participation'


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
        'type',
        'activity_language',
        'room_type',
        'is_active',
        'require_purchase_room',
        'hidden',
        'hide_from_client_admin_panel',
    ) + SafeDeleteAdmin.list_filter

    search_fields = [
        'name_fr',
        'name_en',
    ]

    actions = [
        'undelete_selected',
        'export_admin_action',
        make_reservation_not_refundable,
        make_reservation_refundable,
        export_retreat_sales,
        export_retreat_participation
    ]


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
        UserFilter,
        RetreatFilter,
        'is_active',
        'cancelation_date',
        'cancelation_reason',
        'cancelation_action',
    ) + SafeDeleteAdmin.list_filter

    autocomplete_fields = ['user', 'order_line', 'retreat', 'invitation']

    actions = ['undelete_selected', 'export_admin_action']

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class WaitQueueAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = WaitQueueResource
    list_display = (
        'user',
        'retreat',
        'created_at',
    )
    list_filter = (
        UserFilter,
        RetreatFilter,
        'created_at',
    )
    autocomplete_fields = ('user', 'retreat',)
    search_fields = (
        'user__email',
        'user__username',
        'retreat__name',
    )

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class ReservationAdminInline(admin.TabularInline):
    model = Reservation

    autocomplete_fields = ['user', 'order_line', 'retreat', 'invitation']

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
        RetreatFilter,
        CouponFilter
    ) + SafeDeleteAdmin.list_filter

    search_fields = (
        'name', 'id',
    )

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class WaitQueuePlaceReservedInline(admin.StackedInline):
    model = WaitQueuePlaceReserved
    can_delete = True
    show_change_link = True
    autocomplete_fields = ('user', 'wait_queue_place')
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
        RetreatFilter,
        CancelByFilter
    )
    autocomplete_fields = ('cancel_by', 'retreat')
    search_fields = ('retreat', 'id')

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class WaitQueuePlaceReservedAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'wait_queue_place',
        'user',
        'create',
        'notified',
        'used',
    )
    list_filter = (
        WaitQueuePlaceFilter,
        UserFilter,
        'wait_queue_place__retreat',
        'notified',
        'used',
    )
    autocomplete_fields = ('user', 'wait_queue_place')

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class RetreatDateAdmin(admin.ModelAdmin):
    list_display = (
        'retreat',
        'start_time',
        'end_time',
    )
    list_filter = (
        RetreatFilter,
    )


class AutomaticEmailLogAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'retreat',
        'template_id',
        'sent_at',
    )
    list_filter = (
        ReservationUserFilter,
        ReservationRetreatFilter,
        'sent_at'
    )
    search_fields = ['reservation__user__email', 'email__template_id',
                     'reservation__user__first_name',
                     'reservation__user__last_name']

    def lookup_allowed(self, lookup, value):
        if lookup == "reservation__user":
            return True
        if lookup == "reservation__retreat":
            return True
        return super().lookup_allowed(lookup, value)


class AutomaticEmailAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'retreat_type',
        'time_base',
        'minutes_delta',
        'template_id',
    )
    list_filter = (
        'retreat_type',
        'template_id',
    )


class RetreatUsageLogAdmin(SimpleHistoryAdmin, SafeDeleteAdmin):
    list_display = (
        'user',
        'retreat',
        'datetime',
    )
    list_filter = (
        ReservationUserFilter,
        ReservationRetreatFilter,
    )

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass

    def user(self, obj):
        return obj.reservation.user

    def retreat(self, obj):
        return obj.reservation.retreat

    def lookup_allowed(self, lookup, value):
        if lookup == "reservation__user":
            return True
        if lookup == "reservation__retreat":
            return True
        return super().lookup_allowed(lookup, value)


admin.site.register(Retreat, RetreatAdmin)
admin.site.register(RetreatType)
admin.site.register(RetreatUsageLog, RetreatUsageLogAdmin)
admin.site.register(RetreatDate, RetreatDateAdmin)
admin.site.register(AutomaticEmail, AutomaticEmailAdmin)
admin.site.register(AutomaticEmailLog, AutomaticEmailLogAdmin)
admin.site.register(Picture, PictureAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(WaitQueue, WaitQueueAdmin)
admin.site.register(RetreatInvitation, RetreatInvitationAdmin)
admin.site.register(WaitQueuePlace, WaitQueuePlaceAdmin)
admin.site.register(WaitQueuePlaceReserved, WaitQueuePlaceReservedAdmin)
