import json
from datetime import datetime  # , timedelta
from unittest import mock

import pytz
import responses
from blitz_api.factories import AdminFactory, UserFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ..models import CustomPayment, PaymentProfile
from .paysafe_sample_responses import (SAMPLE_CARD_ALREADY_EXISTS,
                                       SAMPLE_CARD_REFUSED,
                                       SAMPLE_CARD_RESPONSE,
                                       SAMPLE_INVALID_PAYMENT_TOKEN,
                                       SAMPLE_INVALID_SINGLE_USE_TOKEN,
                                       SAMPLE_PAYMENT_RESPONSE,
                                       SAMPLE_PROFILE_RESPONSE)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(
    PAYSAFE={
        'ACCOUNT_NUMBER': "0123456789",
        'USER': "user",
        'PASSWORD': "password",
        'BASE_URL': "http://example.com/",
        'VAULT_URL': "customervault/v1/",
        'CARD_URL': "cardpayments/v1/"
    }
)
class CustomPaymentTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(CustomPaymentTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.custom_payment = CustomPayment.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
            reference_number=751,
            price=123,
            name="test payment",
            details="Description of the test payment",
        )
        cls.custom_payment2 = CustomPayment.objects.create(
            user=cls.admin,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
            reference_number=751,
            price=123,
            name="admin payment",
            details="Description of the admin payment",
        )
        cls.maxDiff = None

    @responses.activate
    def test_create_with_single_use_token(self):
        """
        Ensure we can create a custom payment when provided with a
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'price': "123.00",
            'name': "name of the payment",
            'details': "Description of the payment",
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'authorization_id': '1',
            'details': 'Description of the payment',
            'id': 3,
            'name': 'name of the payment',
            'price': '123.00',
            'settlement_id': '1',
            'transaction_date': response_data['transaction_date'],
            'reference_number': '751',
            'url': 'http://testserver/custom_payments/3',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(response_data, content)

        # Test that one message was sent:
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_with_invalid_single_use_token(self):
        """
        Ensure we can't create a custom payment when provided with a bad
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'price': "123.00",
            'name': "name of the payment",
            'details': "Description of the payment",
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "invalid payment token or payment profile/card "
                "inactive."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_without_permission(self):
        """
        Ensure we can create a custom payment when provided with a
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'price': "123.00",
            'name': "name of the payment",
            'details': "Description of the payment",
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @responses.activate
    def test_create_payment_issue(self):
        """
        Ensure we can't create a custom payment when the payment proccessing
        fails.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_CARD_REFUSED,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'price': "123.00",
            'name': "name of the payment",
            'details': "Description of the payment",
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        content = content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "the request has been declined by the issuing bank."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a custom payment when required field are
        missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field is required.'],
            'price': ['This field is required.'],
            'name': ['This field is required.'],
            'single_use_token': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create a cutom payment when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': None,
            'name': None,
            'details': None,
            'price': None,
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field may not be null.'],
            'name': ['This field may not be null.'],
            'price': ['This field may not be null.'],
            'single_use_token': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a custom payment when required field are
        invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': "invalid",
            'name': (1,),
            'details': (1,),
            'price': "invalid",
            'single_use_token': (1,),
        }

        response = self.client.post(
            reverse('custompayment-list'),
            data,
            format='json',
        )

        content = {
            'details': ['Not a valid string.'],
            'name': ['Not a valid string.'],
            'price': ['A valid number is required.'],
            'single_use_token': ['Not a valid string.'],
            'user': ['Invalid hyperlink - No URL match.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete(self):
        """
        Ensure we can delete a custom payment.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_update(self):
        """
        Ensure we can't update a custom payment.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "new name",
        }

        response = self.client.patch(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_list(self):
        """
        Ensure we can't list cutom payments as an unauthenticated user.
        """
        response = self.client.get(
            reverse('custompayment-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_owner(self):
        """
        Ensure we can list owned custom payments as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('custompayment-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'reference_number': '751',
                'price': "123.00",
                'name': "test payment",
                'details': "Description of the test payment",
                'url': 'http://testserver/custom_payments/1',
                'user': 'http://testserver/users/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_admin(self):
        """
        Ensure we can list all custom payments as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('custompayment-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'reference_number': '751',
                'price': "123.00",
                'name': "test payment",
                'details': "Description of the test payment",
                'url': 'http://testserver/custom_payments/1',
                'user': 'http://testserver/users/1'
            }, {
                'id': 2,
                'transaction_date': data['results'][1]['transaction_date'],
                'authorization_id': '1',
                'reference_number': '751',
                'settlement_id': '1',
                'price': "123.00",
                'name': "admin payment",
                'details': "Description of the admin payment",
                'url': 'http://testserver/custom_payments/2',
                'user': 'http://testserver/users/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can't read a custom payment as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_owner(self):
        """
        Ensure we can read a custom payment owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
            'price': "123.00",
            'name': "test payment",
            'details': "Description of the test payment",
            'url': 'http://testserver/custom_payments/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_owner_not_owned(self):
        """
        Ensure we can't read a custom payment not owned by an authenticated
        user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure we can read any custom payment as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
            'price': "123.00",
            'name': "test payment",
            'details': "Description of the test payment",
            'url': 'http://testserver/custom_payments/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a custom payment that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'custompayment-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
