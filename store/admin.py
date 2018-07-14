from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Membership, Package, Order, OrderLine


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
        'transaction_id',
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


admin.site.register(Membership, MembershipAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderLine, OrderLineAdmin)
