import json

from rest_framework import status
from rest_framework.test import APIClient

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.testing_tools import CustomAPITestCase
from blitz_api.factories import UserFactory, AdminFactory

User = get_user_model()


class ActionLogTests(CustomAPITestCase):

    ATTRIBUTES = [
        'id',
        'url',
        'user',
        'session_key',
        'source',
        'action',
        'additional_data',
        'created',
    ]

    @classmethod
    def setUpClass(cls):
        super(ActionLogTests, cls).setUpClass()

        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def test_create_as_user(self):
        """
        Ensure we can create an ActionLog as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            'http://testserver' + reverse(
                'user-detail',
                kwargs={'pk': self.user.id}
            ),
        )

    def test_create_as_admin(self):
        """
        Ensure we can create an ActionLog as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            'http://testserver' + reverse(
                'user-detail',
                kwargs={'pk': self.admin.id}
            ),
        )

    def test_create_as_unauthenticated(self):
        """
        Ensure we can create an ActionLog as an unauthenticated user.
        """
        data = {
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            None,
        )

    def test_create_as_user_with_additional_data(self):
        """
        Ensure we can create an ActionLog with additional data as
        a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
            'additional_data': json.dumps(
                {
                    'key1': 'value1',
                    'key2': 'value2',
                }
            )
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            'http://testserver' + reverse(
                'user-detail',
                kwargs={'pk': self.user.id}
            ),
        )

    def test_create_as_user_with_wrong_additional_data(self):
        """
        Ensure we can't create an ActionLog with not JSON additional data
        as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
            'additional_data': 12
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

    def test_create_as_user_with_wrong_user(self):
        """
        Ensure we can't create an ActionLog as a simple user if we try to
        put another user as the author.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'user': reverse(
                'user-detail',
                kwargs={'pk': self.admin.pk}
            ),
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            response.json(),
            {'owner': ['Only staffs can specify a user']}
        )

    def test_create_as_user_with_correct_user(self):
        """
        Ensure we can create an ActionLog as a simple user if we try to
        put ourself as the author.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'user': reverse(
                'user-detail',
                kwargs={'pk': self.user.pk}
            ),
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            'http://testserver' + reverse(
                'user-detail',
                kwargs={'pk': self.user.id}
            ),
        )

    def test_create_as_admin_with_user(self):
        """
        Ensure we can create an ActionLog as an admin even if we try to
        put another user as the author.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': reverse(
                'user-detail',
                kwargs={'pk': self.user.pk}
            ),
            'session_key': "my_unique_key",
            'source': "chrono",
            'action': "open_chat",
        }

        response = self.client.post(
            reverse('actionlog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['user'],
            'http://testserver' + reverse(
                'user-detail',
                kwargs={'pk': self.user.id}
            ),
        )
