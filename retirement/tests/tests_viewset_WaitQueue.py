import json
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from blitz_api.factories import AdminFactory, UserFactory

from ..models import Retirement, WaitQueue

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WaitQueueTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(WaitQueueTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retirement = Retirement.objects.create(
            name="mega_retirement",
            details="This is a description of the mega retirement.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            next_user_notified=3,
            accessibility=True,
            form_url="example.com",
        )
        self.wait_queue_subscription = WaitQueue.objects.create(
            user=self.user2,
            retirement=self.retirement,
        )

    def test_create(self):
        """
        Ensure we can subscribe a user to a retirement wait_queue.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            # The 'user' field is ignored when the calling user is not admin.
            # The field is REQUIRED nonetheless.
            'user': reverse('user-detail', args=[self.admin.id]),
        }

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'id': 2,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queues/2',
            'user': ''.join(['http://testserver/users/', str(self.user.id)]),
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(
            json.loads(response.content),
            content
        )

    def test_create_as_admin_for_user(self):
        """
        Ensure we can subscribe another user to a retirement wait_queue as
        an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'id': 2,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queues/2',
            'user': 'http://testserver/users/1',
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(
            json.loads(response.content),
            content
        )

    def test_create_not_authenticated(self):
        """
        Ensure we can't subscribe to a retirement waitqueue if user has no
        permission.
        """

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'Authentication credentials were not provided.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_duplicate(self):
        """
        Ensure we can't subscribe to a retirement waitqueue twice.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            "non_field_errors": [
                "The fields user, retirement must make a unique set."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't subscribe to a retirement waitqueue when required field
        are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            "retirement": ["This field is required."],
            "user": ["This field is required."]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't subscribe to a retirement waitqueue with invalid
        fields.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': (1,),
            'user': "http://testserver/invalid/999"
        }

        response = self.client.post(
            reverse('retirement:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            'retirement': [
                'Incorrect type. Expected URL string, received list.'
            ],
            'user': ['Invalid hyperlink - No URL match.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can't update a subscription to a retirement waitqueue.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_partial_update(self):
        """
        Ensure we can't partially a subscription to a retirement waitqueue.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_delete(self):
        """
        Ensure we can delete a subscription to a retirement waitqueue.
        The index determining the next user to be notified should be corrected.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.retirement.refresh_from_db()
        self.assertEqual(self.retirement.next_user_notified, 2)

    def test_list(self):
        """
        Ensure we can list subscriptions to retirement waitqueues as an
        authenticated user.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse('retirement:waitqueue-list'),
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'created_at': response_data['results'][0]['created_at'],
                'id': 1,
                'retirement': 'http://testserver/retirement/retirements/1',
                'url': 'http://testserver/retirement/wait_queues/1',
                'user': 'http://testserver/users/2'
            }]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_not_authenticated(self):
        """
        Ensure we can't list subscriptions to retirement waitqueues as an
        unauthenticated user.
        """

        response = self.client.get(
            reverse('retirement:waitqueue-list'),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read(self):
        """
        Ensure we can read read a subscription to a retirement as an
        authenticated user.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'id': 1,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queues/1',
            'user': ''.join(['http://testserver/users/', str(self.user2.id)]),
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_not_authenticated(self):
        """
        Ensure we can't read a subscription to a retirement waitqueues as an
        unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_as_admin(self):
        """
        Ensure we can read read a subscription to a retirement as an admin
        user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 1},
            ),
        )

        response_data = json.loads(response.content)

        content = {
            'id': 1,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queues/1',
            'user': ''.join(['http://testserver/users/', str(self.user2.id)]),
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a subscription to a retirement
        that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retirement:waitqueue-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
