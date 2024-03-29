from rest_framework.test import APITestCase

from blitz_api.models import TemporaryToken
from blitz_api.factories import UserFactory
from django.utils import timezone


class TemporaryTokenTests(APITestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_expired_property_false(self):
        """
        Ensure that expired() returns False when the token is not expired
        """
        token = TemporaryToken.objects.create(
            user=self.user
        )

        token.expires = timezone.now() + timezone.timedelta(
            minutes=100
        )

        self.assertEqual(token.expired, False)

    def test_expired_property_true(self):
        """
        Ensure that expired() returns True when the token is expired
        """
        token = TemporaryToken.objects.create(
            user=self.user
        )

        token.expires = timezone.now() - timezone.timedelta(seconds=1)

        # It's already not equal because time is
        # passed since the last line of code
        self.assertEqual(True, token.expired)

    def test_expire_function_true(self):
        """
        Ensure that expire() sets the token as "expired"
        """
        token = TemporaryToken.objects.create(
            user=self.user
        )

        token.expires = timezone.now() + timezone.timedelta(
            minutes=100
        )

        # The token is not expired, 100 minutes remain
        self.assertEqual(False, token.expired)

        token.expire()

        # The token is expired because we ask for
        self.assertEqual(True, token.expired)
