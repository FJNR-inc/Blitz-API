from datetime import timedelta

from django.utils import timezone

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import CreditCard


class CreditCardTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(CreditCardTests, cls).setUpClass()
        cls.user = UserFactory()

    def test_create(self):
        """
        Ensure that we can create a credit card.
        """
        credit_card = CreditCard.objects.create(
            name="Descriptive name",
            owner=self.user,
            expiry_date=timezone.now() + timedelta(weeks=200),
            number="0123456789",
            external_api_id="unique_uuid",
        )

        self.assertEqual(credit_card.__str__(), "Descriptive name")
