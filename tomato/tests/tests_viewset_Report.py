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
        'message',
        'reason',
        'created_at',
    ]

    @classmethod
    def setUpClass(cls):
        super(ReportTests, cls).setUpClass()

        cls.client = APIClient()

        cls.user = UserFactory()

        cls.admin = AdminFactory()

        cls.message = Message.objects.create(
            message="random message",
            user=cls.user,
        )

        cls.report = Report.objects.create(
            message=cls.message,
            user=cls.user,
            reason='random reason',
        )

    def test_create_as_user(self):
        """
        Ensure we can create a report as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'message': reverse(
                'message-detail', args=[self.message.id]
            ),
            'reason': "aggressive content",
        }

        response = self.client.post(
            reverse('report-list'),
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
        Ensure we can create a report as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'message': reverse(
                'message-detail', args=[self.message.id]
            ),
            'reason': "aggressive content",
        }

        response = self.client.post(
            reverse('report-list'),
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
        Ensure we can't create a report without being sign in.
        """

        data = {
            'message': reverse(
                'message-detail', args=[self.message.id]
            ),
            'message': "aggressive content",
        }

        response = self.client.post(
            reverse('report-list'),
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
        Ensure we can list reports as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('report-list'),
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(result['count'], 1)

        for item in result['results']:
            self.check_attributes(item)

    def test_list_as_unauthenticated(self):
        """
        Ensure we can't list reports as an unauthenticated user.
        """

        response = self.client.get(
            reverse('report-list'),
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
