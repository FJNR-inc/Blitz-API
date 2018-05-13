import json

from django.urls import reverse
from django.contrib.auth import get_user_model

from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import TemporaryToken
from ..factories import UserFactory

User = get_user_model()


class TemporaryTokenAuthenticationTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.save()

    def test_authenticate(self):
        """
        Ensure we can authenticate on the platform by providing a valid
        TemporaryToken.
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

        # This could be any url and any method. It is only used to test the
        # token authentication.
        response = self.client.delete(
            reverse(
                'authentication-detail',
                kwargs={'pk': token.key},
            ),
        )

        self.assertFalse(TemporaryToken.objects.filter(key=token.key))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_authenticate_invalid_token(self):
        """
        Ensure we can't authenticate on the platform by providing an invalid
        TemporaryToken.
        """

        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')

        # This could be any url and any method. It is only used to test the
        # token authentication.
        response = self.client.delete(
            reverse(
                'authentication-detail',
                kwargs={'pk': 'invalid_token'},
            ),
        )

        content = {"detail": "Invalid token"}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticate_expired_token(self):
        """
        Ensure we can't authenticate on the platform by providing an expired
        TemporaryToken.
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
        token.expire()

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # This could be any url and any method. It is only used to test the
        # token authentication.
        response = self.client.delete(
            reverse(
                'authentication-detail',
                kwargs={'pk': 'invalid_token'},
            ),
        )

        content = {'detail': 'Token has expired'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticate_inactive_user(self):
        """
        Ensure we can authenticate on the platform by providing a valid
        TemporaryToken.
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

        setattr(self.user, 'is_active', False)
        self.user.save()

        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

        # This could be any url and any method. It is only used to test the
        # token authentication.
        response = self.client.delete(
            reverse(
                'authentication-detail',
                kwargs={'pk': token.key},
            ),
        )

        content = {'detail': 'User inactive or deleted'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
