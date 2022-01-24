import json

from rest_framework import status
from rest_framework.test import (
    APIClient,
    APITestCase,
)

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.testing_tools import CustomAPITestCase
from blitz_api.factories import (
    UserFactory,
    AdminFactory,
)
from tomato.factories import TomatoFactory
from tomato.models import (
    Message,
    Report,
)

User = get_user_model()


class ReportTests(CustomAPITestCase):

    ATTRIBUTES = [
        'id',
        'url',
        'user',
        'number_of_tomato',
        'created_at',
        'updated_at',
    ]

    @classmethod
    def setUpClass(cls):
        super(ReportTests, cls).setUpClass()

        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def test_create_as_user(self):
        """
        Ensure we can log some tomatoes as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'number_of_tomato': 12.5,
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.json(),
        )

        self.check_attributes(response.json())

    def test_create_as_admin(self):
        """
        Ensure we can log some tomatoes as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'number_of_tomato': 12.5,
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.json(),
        )

        self.check_attributes(response.json())

    def test_create_as_unauthenticated(self):
        """
        Ensure we can't log some tomatoes when unauthenticated.
        """

        data = {
            'number_of_tomato': 12.5,
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

        self.assertEqual(
            response.json(),
            {
                "detail": "Authentication credentials were not provided."
            }
        )

    def test_list_as_user(self):
        """
        Ensure we can list tomatoes as a simple user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            9
        )

        for item in result['results']:
            self.check_attributes(item)

    def test_list_as_unauthenticated(self):
        """
        Ensure we can't list tomatoes as an unauthenticated user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
