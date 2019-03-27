"""Store URL Configuration"""
from rest_framework.routers import SimpleRouter, Route
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "store"

router_extra = OptionalSlashSimpleRouter()
router_extra.routes.append(
    Route(
        url=r'^{prefix}/{lookup}/cards/(?P<card_id>[^/]+)$',
        name='{basename}-cards',
        detail=True,
        mapping={
            'delete': 'cards',
        },
        initkwargs={}
    ),
)
router_extra.register('payment_profiles', views.PaymentProfileViewSet)

# Create a router and register our viewsets with it.
router = OptionalSlashSimpleRouter()
router.register('orders', views.OrderViewSet)
router.register('order_lines', views.OrderLineViewSet)
router.register('packages', views.PackageViewSet)
router.register('memberships', views.MembershipViewSet)
router.register('custom_payments', views.CustomPaymentViewSet)
router.register('coupons', views.CouponViewSet)
router.register('coupon_uses', views.CouponUserViewSet)
router.register('refunds', views.RefundViewSet)
# router.register('payment_profiles', views.PaymentProfileViewSet)

router.registry.extend(router_extra.registry)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
