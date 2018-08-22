import json

from unittest import mock

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.core import mail
from django.urls import reverse
from django.test.utils import override_settings

from ..factories import UserFactory
from ..models import ActionToken


class ResetPasswordTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.is_active = False
        self.user.save()

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token(self):
        """
        Ensure we can have a new token to change our password
        """
        data = {
            'email': self.user.email,
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        self.assertEqual(response.content, b'')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(len(tokens) == 1)

        # Test that one message was sent:
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_without_email_param(self):
        """
        Ensure we can't have a new token to change our password without
        giving our email in parameters.
        """
        data = dict()

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        content = {
            'email': ["This field is required."],
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(len(tokens) == 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_with_an_empty_email_param(self):
        """
        Ensure we can't have a new token to change our password with and empty
        email address.
        """
        data = {
            'email': '',
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        content = {
            'email': ["This field may not be blank."],
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(len(tokens) == 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_with_bad_email(self):
        """
        Ensure we can't get a new token to change our password without
        a valid email address.
        """
        data = {
            'email': 'test',
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        content = {'email': ['Enter a valid email address.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(len(tokens) == 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_with_non_existent_email(self):
        """
        Ensure we can't get a new token to change our password without
        a valid email address.
        """
        data = {
            'email': 'test@test.com',
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        content = {'email': ['No account associated to this email address.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(len(tokens) == 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_when_token_already_exist(self):
        """
        Ensure we can get a new token to change our password.
        """
        # We create a token before launch the test
        ActionToken.objects.create(
            user=self.user,
            type='password_change',
        )

        data = {
            'email': self.user.email,
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
            expired=False,
        )

        self.assertEqual(response.content, b'')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(len(tokens) == 1)

        # Test that one message was sent:
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": False,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    def test_create_new_token_without_email_service(self):
        """
        Ensure we can get a new token to change our password.
        """
        data = {
            'email': self.user.email,
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        self.assertEqual(response.content, b'')

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)

        self.assertTrue(len(tokens) == 0)

        # Test that no message was sent:
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.services.EmailMessage.send', return_value=0)
    def test_create_new_token_failure_on_email_service(self, send):
        """
        Ensure we can get a new token to change our password.
        """
        data = {
            'email': self.user.email,
        }

        response = self.client.post(
            reverse('reset_password'),
            data,
            format='json',
        )

        # The token has been created
        tokens = ActionToken.objects.filter(
            user=self.user,
            type='password_change',
        )

        content = {
            'detail': "Your token has been created but no email "
                      "has been sent. Please contact the administration.",
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(len(tokens) == 1)

        # Test that no email was sent:
        self.assertEqual(len(mail.outbox), 0)
