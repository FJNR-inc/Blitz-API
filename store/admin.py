from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from safedelete.admin import SafeDeleteAdmin, highlight_deleted
from simple_history.admin import SimpleHistoryAdmin

from blitz_api.admin import UserFilter, OwnerFilter
from .models import (Membership, Order, OrderLine, Package, PaymentProfile,
                     CustomPayment, Coupon, MembershipCoupon, CouponUser,
                     Refund, BaseProduct, OrderLineBaseProduct, OptionProduct)
from .resources import (MembershipResource, OrderResource, OrderLineResource,
                        PackageResource, CustomPaymentResource, CouponResource,
                        CouponUserResource, RefundResource, )


class CouponFilter(AutocompleteFilter):
    title = 'Coupon'
    field_name = 'coupon'


class OrderUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    rel_model = Order

    @property
    def parameter_name(self):
        return "order__user"

    @parameter_name.setter
    def parameter_name(self, value):
        pass


class OrderLineUserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'
    rel_model = Order

    @property
    def parameter_name(self):
        return "orderline__order__user"

    @parameter_name.setter
    def parameter_name(self, value):
        pass


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Orderlines')
    fk_name = 'order'
    extra = 0
    autocomplete_fields = ('coupon',)


class RefundAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = RefundResource
    list_display = (
        'orderline',
        'amount',
        'refund_date',
    )
    list_filter = (
        'refund_date',
        OrderLineUserFilter
    )
    search_fields = (
        'orderline__order__user__email',
        'orderline__order__user__username',
        'amount',
    )
    autocomplete_fields = ('orderline',)

    def lookup_allowed(self, lookup, value):
        if lookup == "orderline__order__user":
            return True
        return super().lookup_allowed(lookup, value)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class MembershipAdmin(SimpleHistoryAdmin, TranslationAdmin,
                      ExportActionModelAdmin):
    resource_class = MembershipResource
    list_display = (
        'name',
        'price',
        'duration',
    )


class PackageAdmin(SimpleHistoryAdmin, TranslationAdmin,
                   ExportActionModelAdmin):
    resource_class = PackageResource
    list_display = (
        'name',
        'price',
        'reservations',
    )


class CustomPaymentAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = CustomPaymentResource
    list_display = (
        'user',
        'name',
        'price',
    )
    list_filter = (
        UserFilter,
        'transaction_date',
    )
    search_fields = (
        'user__email',
        'user__username',
        'name',
    )
    autocomplete_fields = ('user',)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class OrderAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = OrderResource
    inlines = (OrderLineInline, )
    list_display = (
        'authorization_id',
        'settlement_id',
        'transaction_date',
        'user',
    )
    list_filter = (
        UserFilter,
        'transaction_date',
    )
    search_fields = (
        'user__email',
        'user__username',
    )
    autocomplete_fields = ('user',)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class OrderLineAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    resource_class = OrderLineResource
    list_display = (
        'content_type',
        'content_object',
        'quantity',
        'order',
        'coupon',
        'owner',
        'date'
    )
    list_filter = (
        ('content_type', admin.RelatedOnlyFieldListFilter),
        CouponFilter,
        'quantity',
        OrderUserFilter,
    )
    search_fields = [
        'order__user__email',
        'order__user__username',
        'coupon__code',
        'id'
    ]
    autocomplete_fields = ('order', 'coupon',)

    def owner(self, instance):
        return instance.order.user

    owner.short_description = _('User')
    owner.admin_order_field = 'order__user'

    def date(self, instance):
        return instance.order.transaction_date

    date.short_description = _('Date')
    date.admin_order_field = 'order__transaction_date'

    def lookup_allowed(self, lookup, value):
        if lookup == "order__user":
            return True
        return super().lookup_allowed(lookup, value)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class PaymentProfileAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'owner',
        'external_api_id',
        'external_api_url',
    )
    list_filter = (
        OwnerFilter,
    )
    search_fields = (
        'owner__email',
        'owner__username',
    )
    autocomplete_fields = ('owner',)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class CouponUserInline(admin.StackedInline):
    model = CouponUser
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Coupon users')
    fk_name = 'coupon'
    extra = 0

    autocomplete_fields = ('user', 'coupon',)


class CouponAdmin(SimpleHistoryAdmin, ExportActionModelAdmin):
    inlines = (CouponUserInline, )
    resource_class = CouponResource
    list_display = (
        'code',
        'value',
        'percent_off',
        'owner',
        'details',
    )
    list_filter = (
        OwnerFilter,
    )
    search_fields = (
        'code',
        'owner__email',
        'owner__username',
    )
    autocomplete_fields = ('owner',)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class CouponUserAdmin(SimpleHistoryAdmin, SafeDeleteAdmin,
                      ExportActionModelAdmin, ):
    resource_class = CouponUserResource
    list_display = (
        'user',
        'coupon',
        'uses',
        highlight_deleted,
    )
    list_filter = (
        UserFilter,
        CouponFilter,
    ) + SafeDeleteAdmin.list_display
    search_fields = (
        'coupon__code',
        'user__email',
        'user__username',
    ) + SafeDeleteAdmin.list_filter
    autocomplete_fields = ('user', 'coupon',)

    actions = ['undelete_selected', 'export_admin_action']

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


class OrderLineBaseProductAdmin(SimpleHistoryAdmin, SafeDeleteAdmin,
                                ExportActionModelAdmin, ):
    list_display = (
        'order_line',
        'option',
        'quantity',
    )
    list_filter = (
        'option',
    )
    autocomplete_fields = ('order_line', 'option',)
    search_fields = (
        'order_line__order__user__email',
        'order_line__order__user__username',
        'order_line__coupon__code',
        'id',
        'option__name'
    )


class OptionProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'available'
    )
    list_filter = (
        'available',
    )
    search_fields = (
        'name',
    )


class BaseProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'available'
    )
    list_filter = (
        'available',
    )
    search_fields = (
        'name',
    )


admin.site.register(Membership, MembershipAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(CustomPayment, CustomPaymentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLine, OrderLineAdmin)
admin.site.register(PaymentProfile, PaymentProfileAdmin)
admin.site.register(Coupon, CouponAdmin)
admin.site.register(MembershipCoupon)
admin.site.register(CouponUser, CouponUserAdmin)
admin.site.register(Refund, RefundAdmin)
admin.site.register(BaseProduct, BaseProductAdmin)
admin.site.register(OrderLineBaseProduct, OrderLineBaseProductAdmin)
admin.site.register(OptionProduct, OptionProductAdmin)
