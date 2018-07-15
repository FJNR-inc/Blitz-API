import json

from datetime import timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory

from ..models import CreditCard

User = get_user_model()


class CreditCardTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(CreditCardTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.credit_card = CreditCard.objects.create(
            name="Descriptive name",
            owner=cls.user,
            expiry_date=timezone.now() + timedelta(weeks=200),
            number="0123456789",
            external_api_id="unique_uuid",
        )
        cls.credit_card_admin = CreditCard.objects.create(
            name="Descriptive name",
            owner=cls.admin,
            expiry_date=timezone.now() + timedelta(weeks=200),
            number="0123456789",
            external_api_id="unique_uuid",
        )

    def test_delete_as_admin(self):
        """
        Ensure we can delete any credit card as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )

    def test_delete_as_owner(self):
        """
        Ensure that a user can delete his credit cards.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )

    def test_delete_without_permission(self):
        """
        Ensure that a user can't delete credit cards of other users.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 2},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND
        )

    def test_delete_inexistent(self):
        """
        Ensure that deleting a non-existent credit card does nothing.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 999},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND
        )

    def test_list(self):
        """
        Ensure a user can only list his credit cards.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('creditcard-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'expiry_date': data['results'][0]['expiry_date'],
                'external_api_id': 'unique_uuid',
                'id': 1,
                'name': 'Descriptive name',
                'number': '0123456789',
                'owner': 'http://testserver/users/1',
                'url': 'http://testserver/credit_cards/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_admin(self):
        """
        Ensure we can list all credit cards as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('creditcard-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'expiry_date': data['results'][0]['expiry_date'],
                'external_api_id': 'unique_uuid',
                'id': 1,
                'name': 'Descriptive name',
                'number': '0123456789',
                'owner': 'http://testserver/users/1',
                'url': 'http://testserver/credit_cards/1'
            }, {
                'expiry_date': data['results'][1]['expiry_date'],
                'external_api_id': 'unique_uuid',
                'id': 2,
                'name': 'Descriptive name',
                'number': '0123456789',
                'owner': 'http://testserver/users/2',
                'url': 'http://testserver/credit_cards/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_unauthenticated(self):
        """
        Ensure that unauthenticated users can't list credit cards.
        """
        response = self.client.get(
            reverse('creditcard-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read(self):
        """
        Ensure a user can read his credit cards.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'expiry_date': data['expiry_date'],
            'external_api_id': 'unique_uuid',
            'id': 1,
            'name': 'Descriptive name',
            'number': '0123456789',
            'owner': 'http://testserver/users/1',
            'url': 'http://testserver/credit_cards/1'
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_without_permission(self):
        """
        Ensure a user can't read other users credit cards.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 2},
            ),
        )

        data = json.loads(response.content)

        content = {'detail': "Not found."}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure that an admin can read other users credit cards.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'expiry_date': data['expiry_date'],
            'external_api_id': 'unique_uuid',
            'id': 1,
            'name': 'Descriptive name',
            'number': '0123456789',
            'owner': 'http://testserver/users/1',
            'url': 'http://testserver/credit_cards/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a credit card that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'creditcard-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
