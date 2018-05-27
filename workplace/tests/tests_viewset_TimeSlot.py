import json

from datetime import time, date, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Period, TimeSlot

User = get_user_model()


class TimeSlotTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(TimeSlotTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.period = Period.objects.create(
            name="random_period",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=False,
        )
        cls.period_active = Period.objects.create(
            name="random_period_active",
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.time_slot = TimeSlot.objects.create(
            name="evening_time_slot",
            period=cls.period,
            price=3,
            start_time=time(hour=8),
            end_time=time(hour=12),
            day=date.today(),
        )
        cls.time_slot_active = TimeSlot.objects.create(
            name="evening_time_slot_active",
            period=cls.period_active,
            price=3,
            start_time=time(hour=8),
            end_time=time(hour=12),
            day=date.today(),
        )

    def test_create(self):
        """
        Ensure we can create a timeslot if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=12),
            'end_time': time(hour=16),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'day': date.today().isoformat(),
            'end_time': time(hour=16).isoformat(),
            'name': 'random_time_slot',
            'price': 10,
            'start_time': time(hour=12).isoformat(),
            'url': 'http://testserver/time_slots/3',
            'period': 'http://testserver/periods/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_no_price(self):
        """
        Ensure we can create a timeslot without providing a price.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            # 'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=12),
            'end_time': time(hour=16),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'day': date.today().isoformat(),
            'end_time': time(hour=16).isoformat(),
            'name': 'random_time_slot',
            'price': 3,
            'start_time': time(hour=12).isoformat(),
            'url': 'http://testserver/time_slots/3',
            'period': 'http://testserver/periods/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a timeslot if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            # 'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=12),
            'end_time': time(hour=16),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_overlapping(self):
        """
        Ensure we can't create overlapping timeslot in the same period.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=11),
            'end_time': time(hour=15),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'detail': [
                'An existing timeslot overlaps with the provided start_time '
                'and end_time.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_start_end(self):
        """
        Ensure we can't create timeslots with start_time greater than end_time.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=14),
            'end_time': time(hour=10),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'end_time': ['End time must be later than start_time.'],
            'start_time': ['End time must be earlier than end_time.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_existent_period(self):
        """
        Ensure we can't create a timeslot with a non-existent workplace.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[999]),
            # 'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=12),
            'end_time': time(hour=16),
            'day': date.today(),
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {'period': ['Invalid hyperlink - Object does not exist.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a timeslot when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'day': ['This field is required.'],
            'end_time': ['This field is required.'],
            'name': ['This field is required.'],
            'period': ['This field is required.'],
            'start_time': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_field(self):
        """
        Ensure we can't create a timeslot when required field are blank.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "",
            'period': None,
            'price': None,  # Will use Period's price if not provided
            'start_time': None,
            'end_time': None,
            'day': None,
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'day': ['This field may not be null.'],
            'end_time': ['This field may not be null.'],
            'name': ['This field may not be blank.'],
            'period': ['This field may not be null.'],
            'start_time': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a timeslot when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "",
            'period': "123",
            'price': "",  # Will use Period's price if not provided
            'start_time': "",
            'end_time': "",
            'day': "",
        }

        response = self.client.post(
            reverse('timeslot-list'),
            data,
            format='json',
        )

        content = {
            'day': [
                'Date has wrong format. Use one of these formats instead: '
                'YYYY[-MM[-DD]].'
            ],
            'end_time': [
                'Time has wrong format. Use one of these formats instead: '
                'hh:mm[:ss[.uuuuuu]].'
            ],
            'name': ['This field may not be blank.'],
            'period': ['Invalid hyperlink - No URL match.'],
            'price': ['A valid integer is required.'],
            'start_time': [
                'Time has wrong format. Use one of these formats instead: '
                'hh:mm[:ss[.uuuuuu]].'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a timeslot.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_time_slot",
            'period': reverse('period-detail', args=[self.period.id]),
            'price': 10,  # Will use Period's price if not provided
            'start_time': time(hour=12),
            'end_time': time(hour=16),
            'day': date.today(),
        }

        response = self.client.put(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'day': date.today().isoformat(),
            'end_time': time(hour=16).isoformat(),
            'name': 'random_time_slot',
            'price': 10,
            'start_time': time(hour=12).isoformat(),
            'url': 'http://testserver/time_slots/1',
            'period': 'http://testserver/periods/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a timeslot.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list active timeslots as an unauthenticated user.
        """
        response = self.client.get(
            reverse('timeslot-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'day': date.today().isoformat(),
                'end_time': time(hour=12).isoformat(),
                'name': 'evening_time_slot_active',
                'price': 3,
                'start_time': time(hour=8).isoformat(),
                'url': 'http://testserver/time_slots/2',
                'period': 'http://testserver/periods/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_inactive(self):
        """
        Ensure we can list all timeslots as an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('timeslot-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'day': '2018-05-26',
                'end_time': '12:00:00',
                'name': 'evening_time_slot',
                'period': 'http://testserver/periods/1',
                'price': 3,
                'start_time': '08:00:00',
                'url': 'http://testserver/time_slots/1'
            }, {
                'day': date.today().isoformat(),
                'end_time': time(hour=12).isoformat(),
                'name': 'evening_time_slot_active',
                'price': 3,
                'start_time': time(hour=8).isoformat(),
                'url': 'http://testserver/time_slots/2',
                'period': 'http://testserver/periods/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a timeslot as an unauthenticated user if it is
        active.
        """

        response = self.client.get(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 2},
            ),
        )

        data = json.loads(response.content)

        content = {
            'day': date.today().isoformat(),
            'end_time': time(hour=12).isoformat(),
            'name': 'evening_time_slot_active',
            'price': 3,
            'start_time': time(hour=8).isoformat(),
            'url': 'http://testserver/time_slots/2',
            'period': 'http://testserver/periods/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a timeslot as non_admin if it is inactive.
        """

        response = self.client.get(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_inactive(self):
        """
        Ensure we can read a timeslot as admin if it is inactive.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'day': date.today().isoformat(),
            'end_time': time(hour=12).isoformat(),
            'name': 'evening_time_slot',
            'period': 'http://testserver/periods/1',
            'price': 3,
            'start_time': time(hour=8).isoformat(),
            'url': 'http://testserver/time_slots/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a period that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
