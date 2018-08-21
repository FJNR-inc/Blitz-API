from django.contrib import admin
from .models import (Membership, Package, Order, OrderLine, CreditCard,
                     PaymentProfile,)


class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'duration',
    )


class PackageAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'price',
        'reservations',
    )


class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'authorization_id',
        'settlement_id',
        'transaction_date',
        'user',
    )


class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        'content_type',
        'content_object',
        'quantity',
        'order',
    )


class CreditCardAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'number',
        'expiry_date',
        'owner',
    )


class PaymentProfileAdmin(admin.ModelAdmin):
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
admin.site.register(CreditCard, CreditCardAdmin)
admin.site.register(PaymentProfile, PaymentProfileAdmin)
