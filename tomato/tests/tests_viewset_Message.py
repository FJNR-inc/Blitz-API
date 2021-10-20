import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.testing_tools import CustomAPITestCase
from blitz_api.factories import UserFactory, AdminFactory
from tomato.models import Message

User = get_user_model()


class MessageTests(CustomAPITestCase):

    ATTRIBUTES = [
        'id',
        'url',
        'user',
        'message',
        'posted_at',
    ]

    @classmethod
    def setUpClass(cls):
        super(MessageTests, cls).setUpClass()

        cls.client = APIClient()

        cls.user = UserFactory()

        cls.admin = AdminFactory()

        cls.message = Message.objects.create(
            message="random message",
            user=cls.user,
        )

    def test_create_as_user(self):
        """
        Ensure we can create a message as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'message': "fake message",
        }

        response = self.client.post(
            reverse('message-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

    def test_create_as_admin(self):
        """
        Ensure we can create a message as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'message': "fake message",
        }

        response = self.client.post(
            reverse('message-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

    def test_create_as_unauthenticated(self):
        """
        Ensure we can't create a message without being sign in.
        """

        data = {
            'message': "fake message",
        }

        response = self.client.post(
            reverse('message-list'),
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

    def test_list_as_unauthenticated(self):
        """
        Ensure we can list messages as an unauthenticated user.
        """

        response = self.client.get(
            reverse('message-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.message.id,
                'message': 'random message',
                'user': 'http://testserver/users/' + str(self.user.id),
                'url': 'http://testserver/messages/' + str(self.message.id)
            }]
        }

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(result['count'], 1)

        for item in result['results']:
            self.check_attributes(item)
