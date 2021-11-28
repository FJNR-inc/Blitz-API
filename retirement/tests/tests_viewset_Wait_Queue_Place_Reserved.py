import json
from datetime import datetime, timedelta
from unittest import mock

import pytz
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from blitz_api.factories import RetreatFactory, UserFactory, AdminFactory
from ..models import WaitQueuePlace, WaitQueue, WaitQueuePlaceReserved, \
    Retreat, RetreatDate, RetreatType

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class WaitQueuePlaceReservedTests(APITestCase):

    def setUp(self) -> None:
        self.admin = AdminFactory()

        self.user1 = UserFactory(email='user1@test.com')
        self.user2 = UserFactory(email='user2@test.com')
        self.user3 = UserFactory(email='user3@test.com')
        self.user4 = UserFactory(email='user4@test.com')
        self.user5 = UserFactory(email='user5@test.com')
        self.user6 = UserFactory(email='user6@test.com')
        self.user_cancel = UserFactory()

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
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()

        self.wait_queue_place = WaitQueuePlace.objects.create(
            retreat=self.retreat,
            cancel_by=self.user_cancel
        )

        self.wait_queue_user1 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user1
        )
        self.wait_queue_user2 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user2
        )
        self.wait_queue_user3 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user3
        )
        self.wait_queue_user4 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user4
        )
        self.wait_queue_user5 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user5
        )
        self.wait_queue_user6 = WaitQueue.objects.create(
            retreat=self.retreat,
            user=self.user6
        )
        WaitQueuePlaceReserved.objects.create(
            user=self.user1,
            wait_queue_place=self.wait_queue_place,
        )

    def test_list_wait_queue_place_reserved_as_user(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse(
                'retreat:waitqueueplacereserved-list',
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            response.json()['count'],
            1,
        )

    def test_filter_wait_queue_place_reserved_by_retreat_as_user(self):
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(
            reverse(
                'retreat:waitqueueplacereserved-list',
            ),
            {
                'retreat': str(self.wait_queue_place.retreat.id),
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            response.json()['count'],
            1,
        )

        response = self.client.get(
            reverse(
                'retreat:waitqueueplacereserved-list',
            ),
            {
                'retreat': '999',
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            response.json()['count'],
            0,
        )
