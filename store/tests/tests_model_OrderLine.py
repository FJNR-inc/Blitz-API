from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import AcademicLevel

from ..models import OrderLine, Order, Package, Coupon


class OrderTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.coupon = Coupon.objects.create(
            value=13,
            code="12345678",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for fjeanneau clients",
            owner=cls.user,
        )

    def test_create(self):
        """
        Ensure that we can create an order line.
        """
        order_line = OrderLine.objects.create(
            order=self.order,
            quantity=999,
            content_type=self.package_type,
            object_id=1,
            coupon=self.coupon,
        )

        self.assertEqual(str(order_line), 'extreme_package, qt:999')
