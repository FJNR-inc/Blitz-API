import json
import pytz

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Period, TimeSlot, Workplace, Reservation

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ReservationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.workplace = Workplace.objects.create(
            name="Blitz",
            seats=40,
            details="short_description",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.workplace2 = Workplace.objects.create(
            name="Blitz2",
            seats=1,
            details="short_description",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.period = Period.objects.create(
            name="random_period",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=False,
        )
        cls.period_active = Period.objects.create(
            name="random_period_active",
            workplace=cls.workplace2,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.period_no_workplace = Period.objects.create(
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
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        cls.time_slot_active = TimeSlot.objects.create(
            name="evening_time_slot_active",
            period=cls.period_active,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 18)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 22)),
        )
        cls.time_slot_overlap = TimeSlot.objects.create(
            name="evening_time_slot2",
            period=cls.period,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 20)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 23)),
        )
        cls.time_slot_no_workplace = TimeSlot.objects.create(
            name="evening_time_slot",
            period=cls.period_no_workplace,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        cls.reservation = Reservation.objects.create(
            user=cls.user,
            timeslot=cls.time_slot_active,
            is_active=True,
        )
        cls.reservation_admin = Reservation.objects.create(
            user=cls.admin,
            timeslot=cls.time_slot_active,
            is_active=True,
        )

    def test_create(self):
        """
        Ensure we can create a reservation if user has permission.
        It is possible to create reservations for INACTIVE time slots.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'id': 3,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/1',
            'url': 'http://testserver/reservations/3',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a reservation if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
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
        Ensure we can't create reservations with overlapping timeslots for the
        same user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot_overlap.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'This reservation overlaps with another active reservations '
                'for this user.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate(self):
        """
        Ensure we can create the same reservation multiple times. This does
        not duplicate the entry and instead returns the existing one.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot_active.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'id': 3,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/3',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_no_workplace(self):
        """
        Ensure we can't create reservations for time slots that are part of a
        period without workplace, and thus has no `seats` count.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot_no_workplace.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'No reservation are allowed for time slots without workplace.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_existent_period_user(self):
        """
        Ensure we can't create a reservation with a non-existent timeslot or
        user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse('timeslot-detail', args=[999]),
            'user': reverse('user-detail', args=[999]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'timeslot': ['Invalid hyperlink - Object does not exist.'],
            'user': ['Invalid hyperlink - Object does not exist.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a reservation when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field is required.'],
            'timeslot': ['This field is required.'],
            'is_active': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_field(self):
        """
        Ensure we can't create a reservation when required field are blank.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': None,
            'timeslot': None,
            'is_active': None,
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field may not be null.'],
            'timeslot': ['This field may not be null.'],
            'is_active': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a reservation when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': "invalid",
            'timeslot': "invalid",
            'is_active': "invalid",
        }

        response = self.client.post(
            reverse('reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['Invalid hyperlink - No URL match.'],
            'timeslot': ['Invalid hyperlink - No URL match.'],
            'is_active': ['"invalid" is not a valid boolean.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a reservation.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'timeslot': reverse(
                'timeslot-detail', args=[self.time_slot.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': False,
        }

        response = self.client.put(
            reverse(
                'reservation-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'id': 1,
            'is_active': False,
            'timeslot': 'http://testserver/time_slots/1',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial(self):
        """
        Ensure we can partially update a reservation.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_active': False,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'id': 1,
            'is_active': False,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can't delete a reservation.
        Reservation should be updated to inactive.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'reservation-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_501_NOT_IMPLEMENTED)

    def test_list(self):
        """
        Ensure we can list reservations as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/1',
                'user': 'http://testserver/users/1'
            }, {
                'id': 2,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/2',
                'user': 'http://testserver/users/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_non_admin(self):
        """
        Ensure that a user can list its reservations.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/1',
                'user': 'http://testserver/users/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure that a user can read one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'reservation-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'id': 1,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a reservation as non_admin if it is not owned.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'reservation-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a period that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'timeslot-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
