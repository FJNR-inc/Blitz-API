from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Membership, Order, OrderLine, Package, PaymentProfile


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    can_delete = True
    verbose_name_plural = _('Orderlines')
    fk_name = 'order'
    extra = 0


class MembershipAdmin(SimpleHistoryAdmin, TranslationAdmin):
    list_display = (
        'name',
        'price',
        'duration',
    )


class PackageAdmin(SimpleHistoryAdmin, TranslationAdmin):
    list_display = (
        'name',
        'price',
        'reservations',
    )


class OrderAdmin(SimpleHistoryAdmin):
    inlines = (OrderLineInline, )
    list_display = (
        'authorization_id',
        'settlement_id',
        'transaction_date',
        'user',
    )
    list_filter = (
        ('user', admin.RelatedOnlyFieldListFilter),
        'transaction_date',
    )
    search_fields = (
        'user__email',
        'user__username',
    )


class OrderLineAdmin(SimpleHistoryAdmin):
    list_display = (
        'content_type',
        'content_object',
        'quantity',
        'order',
        'owner',
    )
    list_filter = (
        ('content_type', admin.RelatedOnlyFieldListFilter),
        'quantity',
        ('order__user', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'order__email',
        'order__username',
    )

    def owner(self, instance):
        return instance.order.user

    owner.short_description = _('User')
    owner.admin_order_field = 'order__user'


class PaymentProfileAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'owner',
        'external_api_id',
        'external_api_url',
    )
    list_filter = (
        ('owner', admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        'owner__email',
        'owner__username',
    )


admin.site.register(Membership, MembershipAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLine, OrderLineAdmin)
admin.site.register(PaymentProfile, PaymentProfileAdmin)
