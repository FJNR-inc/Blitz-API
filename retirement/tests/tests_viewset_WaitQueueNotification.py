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

from ..models import Retirement, WaitQueue, WaitQueueNotification

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
            reserved_seats=4,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
        )

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)
        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            self.wait_queue_notif = WaitQueueNotification.objects.create(
                user=self.user2,
                retirement=self.retirement,
            )

    def test_create(self):
        """
        Ensure we can't create a notification.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.post(
            reverse(
                'retirement:waitqueuenotification-list',
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retirement:waitqueuenotification-detail',
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.put(
            reverse(
                'retirement:waitqueuenotification-detail',
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
                'retirement:waitqueuenotification-detail',
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
            reverse('retirement:waitqueuenotification-list'),
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
                'url': 'http://testserver/retirement/'
                       'wait_queue_notifications/1',
                'user': 'http://testserver/users/2'
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
            reverse('retirement:waitqueuenotification-list'),
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
                'url': 'http://testserver/retirement/'
                       'wait_queue_notifications/1',
                'user': 'http://testserver/users/2'
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
            reverse('retirement:waitqueuenotification-list'),
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
        Ensure we can't list subscriptions to retirement waitqueues as an
        unauthenticated user.
        """
        response = self.client.get(
            reverse('retirement:waitqueuenotification-list'),
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
                'retirement:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'id': 1,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queue_notifications/1',
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
                'retirement:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'id': 1,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/wait_queue_notifications/1',
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
                'retirement:waitqueuenotification-detail',
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
                'retirement:waitqueuenotification-detail',
                kwargs={'pk': 1},
            ),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a subscription to a retirement
        that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retirement:waitqueuenotification-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notify(self):
        """
        Ensure we can notify for reserved places.
        """
        # self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        # Old notification that will be deleted
        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            WaitQueueNotification.objects.create(
                user=self.user,
                retirement=self.retirement,
            )

        waiting_user = WaitQueue.objects.create(
            user=self.user,
            retirement=self.retirement,
        )

        waiting_user2 = WaitQueue.objects.create(
            user=self.user2,
            retirement=self.retirement,
        )

        notification_count = WaitQueueNotification.objects.all().count()

        response = self.client.get(
            '/'.join([
                reverse('retirement:waitqueuenotification-list'),
                'notify',
            ])
        )

        self.retirement.refresh_from_db()

        # Assert that the wait queue index is updated
        # All users (2) are notified since there are more (4) reserved_seats
        self.assertEqual(
            self.retirement.next_user_notified,
            2,
            "next_user_notified index invalid"
        )

        # Assert that only 2 reserved seats remain (since only 2 users are
        # waiting)
        self.assertEqual(
            self.retirement.reserved_seats,
            2,
            "reserved_seats index invalid"
        )

        # Assert that 2 new notifications are created (2 users in wait_queue)
        # Assert that 2 old notification has been deleted (too old)
        self.assertEqual(
            WaitQueueNotification.objects.all().count(),
            notification_count + 2 - 2,
            "WaitQueueNotification count invalid"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(len(mail.outbox), 2)

        waiting_user.delete()
        waiting_user2.delete()

    def test_notify_reached_end_of_wait_queue(self):
        """
        Ensure we get a proper response if no users remain in any
        retirements' wait_queue.
        """
        # self.client.force_authenticate(user=self.admin)

        notification_count = WaitQueueNotification.objects.all().count()

        self.retirement.next_user_notified = 2
        self.retirement.save()

        response = self.client.get(
            '/'.join([
                reverse('retirement:waitqueuenotification-list'),
                'notify',
            ])
        )

        self.retirement.refresh_from_db()

        self.assertEqual(
            self.retirement.next_user_notified,
            0,
            "next_user_notified index invalid"
        )

        # Assert that 0 reserved seats remain (since 0 users are waiting)
        self.assertEqual(
            self.retirement.reserved_seats,
            0,
            "reserved_seats index invalid"
        )

        # Assert that 0 notification has been created
        # The old one has been deleted
        self.assertEqual(
            WaitQueueNotification.objects.all().count(),
            notification_count - 1,
            "WaitQueueNotification count invalid"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            'detail': 'No reserved seats.',
            'stop': True
        }

        self.assertEqual(response_data, content)

        self.assertEqual(len(mail.outbox), 0)

    def test_notify_no_reserved_seats(self):
        """
        Ensure we get a proper response if no reserved seats remain in any
        retirement.
        """
        # self.client.force_authenticate(user=self.admin)

        self.retirement.reserved_seats = 0
        self.retirement.save()

        response = self.client.get(
            '/'.join([
                reverse('retirement:waitqueuenotification-list'),
                'notify',
            ])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            'detail': 'No reserved seats.',
            'stop': True
        }

        self.assertEqual(response_data, content)

    def test_notify_delay_not_elapsed(self):
        """
        Ensure we get a proper response if the last notification is not older
        than 24h.
        """
        # self.client.force_authenticate(user=self.admin)

        self.wait_queue_notif = WaitQueueNotification.objects.create(
            user=self.user2,
            retirement=self.retirement,
        )

        response = self.client.get(
            '/'.join([
                reverse('retirement:waitqueuenotification-list'),
                'notify',
            ])
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            'detail': 'Last notification was sent less than 24h ago.'
        }

        self.assertEqual(response_data, content)
