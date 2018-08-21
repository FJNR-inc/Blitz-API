"""Store URL Configuration"""
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "store"

# Create a router and register our viewsets with it.
router = OptionalSlashSimpleRouter()
router.register('orders', views.OrderViewSet)
router.register('order_lines', views.OrderLineViewSet)
router.register('packages', views.PackageViewSet)
router.register('memberships', views.MembershipViewSet)
router.register('credit_cards', views.CreditCardViewSet)
router.register('payment_profiles', views.PaymentProfileViewSet)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
