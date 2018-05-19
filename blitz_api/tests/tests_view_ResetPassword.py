import json

from unittest import mock

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

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
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token(self, imailing):
        """
        Ensure we can have a new token to change our password
        """
        data = {
            'email': self.user.email,
        }

        instance_imailing = imailing.create_instance.return_value
        instance_imailing.send_templated_email.return_value = {
            "code": "success",
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

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_without_email_param(self, imailing):
        """
        Ensure we can't have a new token to change our password without
        give our email in param
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
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_with_an_empty_email_param(self, imailing):
        """
        Ensure we can't have a new token to change our password without
        give our email in param
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
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_with_bad_email(self, imailing):
        """
        Ensure we can't have a new token to change our password without
        a valid email
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
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_with_non_existent_email(self, imailing):
        """
        Ensure we can't have a new token to change our password without
        a valid email
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
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_when_token_already_exist(self, imailing):
        """
        Ensure we can have a new token to change our password
        """
        # We create a token before launch the test
        ActionToken.objects.create(
            user=self.user,
            type='password_change',
        )

        data = {
            'email': self.user.email,
        }

        instance_imailing = imailing.create_instance.return_value
        instance_imailing.send_templated_email.return_value = {
            "code": "success",
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

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": False,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_without_email_service(self, imailing):
        """
        Ensure we can have a new token to change our password
        """
        data = {
            'email': self.user.email,
        }

        instance_imailing = imailing.create_instance.return_value
        instance_imailing.send_templated_email.return_value = {
            "code": "success",
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

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "FORGOT_PASSWORD_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.views.IMailing')
    def test_create_new_token_with_failure_on_email_service(self, imailing):
        """
        Ensure we can have a new token to change our password
        """
        data = {
            'email': self.user.email,
        }

        instance_imailing = imailing.create_instance.return_value
        instance_imailing.send_templated_email.return_value = {
            "code": "failure",
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
