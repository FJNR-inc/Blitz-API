from django_filters import rest_framework as filters

from gm2m import GM2MField

from .models import Coupon


class CouponFilter(filters.FilterSet):
    """
    This custom filter should handle GM2MField.
    For now, the 'applicable_products' field is simply not filtered.
    """

    class Meta:
        model = Coupon
        exclude = ['applicable_products']
