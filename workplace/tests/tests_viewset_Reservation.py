import json
import pytz

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from unittest import mock

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

        response_data = json.loads(response.content)
        del response_data['user_details']["first_name"]
        del response_data['user_details']["last_name"]
        del response_data['user_details']["email"]
        del response_data['user_details']['date_joined']

        content = {
            'id': 3,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/1',
            'url': 'http://testserver/reservations/3',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_reason': None,
            'timeslot_details': {
                'end_time': '2130-01-15T12:00:00-05:00',
                'id': 1,
                'period': 'http://testserver/periods/1',
                'places_remaining': 39,
                'reservations': ['http://testserver/reservations/3'],
                'reservations_canceled': [],
                'price': '3.00',
                'start_time': '2130-01-15T08:00:00-05:00',
                'url': 'http://testserver/time_slots/1',
                'users': ['http://testserver/users/1'],
                'workplace': {
                    'address_line1': '123 random street',
                    'address_line2': None,
                    'city': '',
                    'country': 'Random country',
                    'details': 'short_description',
                    'id': 1,
                    'latitude': None,
                    'longitude': None,
                    'name': 'Blitz',
                    'pictures': [],
                    'postal_code': '123 456',
                    'seats': 40,
                    'state_province': 'Random state',
                    'timezone': None,
                    'url': 'http://testserver/workplaces/1'
                }
            },
            'user_details': {
                'academic_field': None,
                'academic_level': None,
                'birthdate': None,
                'gender': None,
                'groups': [],
                'id': 1,
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'last_login': None,
                'membership': None,
                'membership_end': None,
                'other_phone': None,
                'phone': None,
                'tickets': 1,
                'university': None,
                'url': 'http://testserver/users/1',
                'user_permissions': []
            }
        }

        self.assertEqual(response_data, content)

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

        response_data = json.loads(response.content)
        del response_data['user_details']["first_name"]
        del response_data['user_details']["last_name"]
        del response_data['user_details']["email"]
        del response_data['user_details']['date_joined']

        content = {
            'id': 3,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/3',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_reason': None,
            'timeslot_details': {
                'end_time': '2130-01-15T22:00:00-05:00',
                'id': 2,
                'period': 'http://testserver/periods/2',
                'places_remaining': -2,
                'reservations': [
                    'http://testserver/reservations/1',
                    'http://testserver/reservations/2',
                    'http://testserver/reservations/3'
                ],
                'reservations_canceled': [],
                'price': '3.00',
                'start_time': '2130-01-15T18:00:00-05:00',
                'url': 'http://testserver/time_slots/2',
                'users': [
                    'http://testserver/users/1',
                    'http://testserver/users/2',
                    'http://testserver/users/1'
                ],
                'workplace': {
                    'address_line1': '123 random street',
                    'address_line2': None,
                    'city': '',
                    'country': 'Random country',
                    'details': 'short_description',
                    'id': 2,
                    'latitude': None,
                    'longitude': None,
                    'name': 'Blitz2',
                    'pictures': [],
                    'postal_code': '123 456',
                    'seats': 1,
                    'state_province': 'Random state',
                    'timezone': None,
                    'url': 'http://testserver/workplaces/2'
                }
            },
            'user_details': {
                'academic_field': None,
                'academic_level': None,
                'birthdate': None,
                'gender': None,
                'groups': [],
                'id': 1,
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'last_login': None,
                'membership': None,
                'membership_end': None,
                'other_phone': None,
                'phone': None,
                'tickets': 1,
                'university': None,
                'url': 'http://testserver/users/1',
                'user_permissions': []
            }
        }

        self.assertEqual(response_data, content)

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

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['timeslot_details']

        content = {
            'id': 1,
            'is_active': False,
            'timeslot': 'http://testserver/time_slots/1',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

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

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['timeslot_details']

        content = {
            'id': 1,
            'is_active': False,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        del data['results'][0]['user_details']
        del data['results'][0]['timeslot_details']
        del data['results'][1]['user_details']
        del data['results'][1]['timeslot_details']

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/1',
                'user': 'http://testserver/users/1',
                'cancelation_date': None,
                'cancelation_reason': None
            }, {
                'id': 2,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/2',
                'user': 'http://testserver/users/2',
                'cancelation_date': None,
                'cancelation_reason': None
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_non_admin(self):
        """
        Ensure that a user can list its reservations.
        Be wary: a user can see the list of user ID that are associated with
                 the reservation's timeslot.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        del data['results'][0]['user_details']
        del data['results'][0]['timeslot_details']

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'is_active': True,
                'timeslot': 'http://testserver/time_slots/2',
                'url': 'http://testserver/reservations/1',
                'user': 'http://testserver/users/1',
                'cancelation_date': None,
                'cancelation_reason': None
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

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['timeslot_details']

        content = {
            'id': 1,
            'is_active': True,
            'timeslot': 'http://testserver/time_slots/2',
            'url': 'http://testserver/reservations/1',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

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

    def test_delete(self):
        """
        Ensure that a user can delete one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    kwargs={'pk': 1},
                ),
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

    def test_delete_as_admin(self):
        """
        Ensure that an admin can delete any reservations.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    kwargs={'pk': 1},
                ),
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

    def test_delete_not_owner(self):
        """
        Ensure that a user can't delete a reservation that he doesn't own.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'reservation-detail',
                kwargs={'pk': self.reservation_admin.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_twice(self):
        """
        Ensure that a user can delete one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    kwargs={'pk': 1},
                ),
            )

        response = self.client.delete(
            reverse(
                'reservation-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None
