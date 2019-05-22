from datetime import timedelta

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import Membership, Order, OrderLine, Refund


class RefundTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(RefundTests, cls).setUpClass()
        cls.membership_type = ContentType.objects.get_for_model(Membership)
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        cls.user = UserFactory()
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.orderline = OrderLine.objects.create(
            order=cls.order,
            quantity=999,
            content_type=cls.membership_type,
            object_id=cls.membership.id,
        )

    def test_create(self):
        """
        Ensure that we can create a membership.
        """
        refund = Refund.objects.create(
            orderline=self.orderline,
            refund_date=timezone.now(),
            amount=10.00,
            details="Refund details",
        )

        self.assertEqual(str(refund), 'basic_membership, qt:999, 10.0$')
