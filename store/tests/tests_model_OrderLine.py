from django.utils import timezone

from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import AcademicLevel

from ..models import OrderLine, Order, Package


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

    def test_create(self):
        """
        Ensure that we can create an order line.
        """
        order_line = OrderLine.objects.create(
            order=self.order,
            quantity=999,
            content_type=self.package_type,
            object_id=1,
        )

        self.assertEqual(str(order_line), 'extreme_package, qt:999')
