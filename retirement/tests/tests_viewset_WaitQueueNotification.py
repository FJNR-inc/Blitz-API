import json
from datetime import datetime, timedelta
from unittest import mock

import pytz
from blitz_api.factories import AdminFactory, UserFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from ..models import Retreat, WaitQueue, WaitQueueNotification

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WaitQueueNotificationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(WaitQueueNotificationTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.user2 = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
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
            reserved_seats=4,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
        )

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)
        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            self.wait_queue_notif = WaitQueueNotification.objects.create(
                user=self.user2,
                retreat=self.retreat,
            )

    def test_create(self):
        """
        Ensure we can't create a notification.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.post(
            reverse(
                'retreat:waitqueuenotification-list',
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update(self):
        """
        Ensure we can't update a notification.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retreat:waitqueuenotification-detail',
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
        Ensure we can't partially a notification.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retreat:waitqueuenotification-detail',
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
        Ensure we can't delete a notification.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_list(self):
        """
        Ensure we can list notifications that have been made.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('retreat:waitqueuenotification-list'),
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'created_at': response_data['results'][0]['created_at'],
                'id': self.wait_queue_notif.id,
                'retreat':
                    'http://testserver/retreat/retreats/' +
                    str(self.retreat.id),
                'url': 'http://testserver/retreat/'
                       'wait_queue_notifications/' +
                       str(self.wait_queue_notif.id),
                'user': 'http://testserver/users/' + str(self.user2.id)
            }]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_not_admin(self):
        """
        Ensure we can list owned notifications as a normal user.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse('retreat:waitqueuenotification-list'),
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'created_at': response_data['results'][0]['created_at'],
                'id': self.wait_queue_notif.id,
                'retreat':
                    'http://testserver/retreat/retreats/' +
                    str(self.retreat.id),
                'url': 'http://testserver/retreat/'
                       'wait_queue_notifications/' +
                       str(self.wait_queue_notif.id),
                'user': 'http://testserver/users/' + str(self.user2.id)
            }]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_not_admin2(self):
        """
        Ensure we can list owned notifications as a normal user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('retreat:waitqueuenotification-list'),
            format='json',
        )

        content = {
            'count': 0,
            'next': None,
            'previous': None,
            'results': [],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_not_authenticated(self):
        """
        Ensure we can't list subscriptions to retreat waitqueues as an
        unauthenticated user.
        """
        response = self.client.get(
            reverse('retreat:waitqueuenotification-list'),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read(self):
        """
        Ensure we can read read a notification.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': self.wait_queue_notif.id},
            ),
        )

        content = {
            'id': self.wait_queue_notif.id,
            'retreat':
                'http://testserver/retreat/retreats/' +
                str(self.retreat.id),
            'url':
                'http://testserver/retreat/wait_queue_notifications/' +
                str(self.wait_queue_notif.id),
            'user': ''.join(['http://testserver/users/', str(self.user2.id)]),
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_not_admin(self):
        """
        Ensure we can read read a notification if owned.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': self.wait_queue_notif.id},
            ),
        )

        content = {
            'id': self.wait_queue_notif.id,
            'retreat':
                'http://testserver/retreat/retreats/' +
                str(self.retreat.id),
            'url':
                'http://testserver/retreat/wait_queue_notifications/' +
                str(self.wait_queue_notif.id),
            'user': ''.join(['http://testserver/users/', str(self.user2.id)]),
            'created_at': json.loads(response.content)['created_at'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_not_admin2(self):
        """
        Ensure we can't read a notification if not owned.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_not_authenticated(self):
        """
        Ensure we can't read a notification as an unauthenticated user.
        """
        response = self.client.get(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a subscription to a retreat
        that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:waitqueuenotification-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
