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

from ..models import Retreat, WaitQueue, RetreatType, RetreatDate

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
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()
        self.wait_queue_subscription = WaitQueue.objects.create(
            user=self.user2,
            retreat=self.retreat,
        )

    def test_create(self):
        """
        Ensure we can subscribe a user to a retreat wait_queue.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            # The 'user' field is ignored when the calling user is not admin.
            # The field is REQUIRED nonetheless.
            'user': reverse('user-detail', args=[self.admin.id]),
        }

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'list_size': 2,
            'notified': False,
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.retreat.id),
            'user': ''.join(['http://testserver/users/', str(self.user.id)]),
            'created_at': json.loads(response.content)['created_at'],
            'used': False,
        }

        response_data = json.loads(response.content)
        del response_data['id']
        del response_data['url']

        self.assertEqual(
            response_data,
            content
        )

    def test_create_as_admin_for_user(self):
        """
        Ensure we can subscribe another user to a retreat wait_queue as
        an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'list_size': 2,
            'notified': False,
            'retreat': 'http://testserver/retreat/retreats/' + str(
                self.retreat.id
            ),
            'user': {
                'id': self.user.id,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'personnal_restrictions': self.user.personnal_restrictions,
                'phone': self.user.phone,
                'url': 'http://testserver' + reverse(
                    'user-detail',
                    args=[self.user.id],
                ),
            },
            'used': False,
        }

        response_data = json.loads(response.content)
        del response_data['id']
        del response_data['url']
        del response_data['created_at']

        self.assertEqual(
            response_data,
            content
        )

    def test_create_not_authenticated(self):
        """
        Ensure we can't subscribe to a retreat waitqueue if user has no
        permission.
        """

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
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
        Ensure we can't subscribe to a retreat waitqueue twice.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user2.id]),
        }

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            "non_field_errors": [
                "The fields user, retreat must make a unique set."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't subscribe to a retreat waitqueue when required field
        are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            "retreat": ["This field is required."],
            "user": ["This field is required."]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't subscribe to a retreat waitqueue with invalid
        fields.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': (1,),
            'user': "http://testserver/invalid/999"
        }

        response = self.client.post(
            reverse('retreat:waitqueue-list'),
            data,
            format='json',
        )

        content = {
            'retreat': [
                'Incorrect type. Expected URL string, received list.'
            ],
            'user': ['Invalid hyperlink - No URL match.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can't update a subscription to a retreat waitqueue.
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
                'retreat:waitqueue-detail',
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
        Ensure we can't partially a subscription to a retreat waitqueue.
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
                'retreat:waitqueue-detail',
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
        Ensure we can delete a subscription to a retreat waitqueue.
        The index determining the next user to be notified should be corrected.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retreat:waitqueue-detail',
                kwargs={'pk': self.wait_queue_subscription.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

    def test_list(self):
        """
        Ensure we can list subscriptions to retreat waitqueues as an
        authenticated user.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse('retreat:waitqueue-list'),
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'created_at': response_data['results'][0]['created_at'],
                'id': self.wait_queue_subscription.id,
                'list_size': 1,
                'notified': False,
                'retreat':
                    'http://testserver/retreat/retreats/' +
                    str(self.retreat.id),
                'url':
                    'http://testserver/retreat/wait_queues/' +
                    str(self.wait_queue_subscription.id),
                'used': False,
                'user': 'http://testserver/users/' + str(self.user2.id)
            }]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_not_authenticated(self):
        """
        Ensure we can't list subscriptions to retreat waitqueues as an
        unauthenticated user.
        """

        response = self.client.get(
            reverse('retreat:waitqueue-list'),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read(self):
        """
        Ensure we can read read a subscription to a retreat as an
        authenticated user.
        """
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(
            reverse(
                'retreat:waitqueue-detail',
                kwargs={'pk': self.wait_queue_subscription.id},
            ),
        )

        content = {
            'id': self.wait_queue_subscription.id,
            'list_size': 1,
            'notified': False,
            'retreat':
                'http://testserver/retreat/retreats/' +
                str(self.retreat.id),
            'url':
                'http://testserver/retreat/wait_queues/' +
                str(self.wait_queue_subscription.id),
            'user': ''.join(['http://testserver/users/', str(self.user2.id)]),
            'created_at': json.loads(response.content)['created_at'],
            'used': False,
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_not_authenticated(self):
        """
        Ensure we can't read a subscription to a retreat waitqueues as an
        unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'retreat:waitqueue-detail',
                kwargs={'pk': 1},
            ),
            format='json',
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_as_admin(self):
        """
        Ensure we can read read a subscription to a retreat as an admin
        user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:waitqueue-detail',
                kwargs={'pk': self.wait_queue_subscription.id},
            ),
        )

        response_data = json.loads(response.content)

        content = {
            'id': self.wait_queue_subscription.id,
            'list_size': 1,
            'notified': False,
            'retreat': 'http://testserver/retreat/retreats/' + str(
                self.retreat.id
            ),
            'url': 'http://testserver/retreat/wait_queues/' + str(
                self.wait_queue_subscription.id
            ),
            'user': {
                'id': self.user2.id,
                'email': self.user2.email,
                'first_name': self.user2.first_name,
                'last_name': self.user2.last_name,
                'personnal_restrictions': self.user2.personnal_restrictions,
                'phone': self.user2.phone,
                'url': 'http://testserver' + reverse(
                    'user-detail',
                    args=[self.user2.id],
                ),
            },
            'created_at': json.loads(response.content)['created_at'],
            'used': False,
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a subscription to a retreat
        that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:waitqueue-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
