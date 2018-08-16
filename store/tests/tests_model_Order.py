from django.utils import timezone

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import AcademicLevel

from ..models import Order


class OrderTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderTests, cls).setUpClass()
        cls.user = UserFactory()

    def test_create(self):
        """
        Ensure that we can create a order.
        """
        order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        self.assertEqual(str(order), '1')
