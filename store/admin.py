from django.contrib import admin

from simple_history.admin import SimpleHistoryAdmin

from .models import Membership, Package, Order, OrderLine, PaymentProfile


class MembershipAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'price',
        'duration',
    )


class PackageAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'price',
        'reservations',
    )


class OrderAdmin(SimpleHistoryAdmin):
    list_display = (
        'authorization_id',
        'settlement_id',
        'transaction_date',
        'user',
    )


class OrderLineAdmin(SimpleHistoryAdmin):
    list_display = (
        'content_type',
        'content_object',
        'quantity',
        'order',
    )


class PaymentProfileAdmin(SimpleHistoryAdmin):
    list_display = (
        'name',
        'owner',
        'external_api_id',
        'external_api_url',

    )


admin.site.register(Membership, MembershipAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLine, OrderLineAdmin)
admin.site.register(PaymentProfile, PaymentProfileAdmin)
