import json

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import TemporaryToken
from ..factories import UserFactory

User = get_user_model()


class TemporaryTokenDestroyTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.save()

    def test_logout(self):
        """
        Ensure we can logout of the platform.
        This deletes the TemporaryToken assigned to the user.
        """
        data = {
            'username': self.user.username,
            'password': 'Test123!'
        }

        response = self.client.post(reverse('token_api'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        token = TemporaryToken.objects.get(
            user__username=self.user.username,
        )

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        response = self.client.delete(
            reverse(
                'authentication-detail',
                kwargs={'pk': token.key},
            ),
        )

        self.assertFalse(TemporaryToken.objects.filter(key=token.key))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
