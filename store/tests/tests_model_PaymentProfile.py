from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import PaymentProfile


class PaymentProfileTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PaymentProfileTests, cls).setUpClass()
        cls.user = UserFactory()

    def test_create(self):
        """
        Ensure that we can create a payment profile.
        """
        payment_profile = PaymentProfile.objects.create(
            name="Test profile",
            owner=self.user,
            external_api_id="123",
            external_api_url="https://example.com/customervault/v1/profiles/",
        )

        self.assertEqual(payment_profile.__str__(), "Test profile")
