import json
import pytz

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from unittest import mock

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Period, TimeSlot, Workplace, Reservation
from tomato.models import Tomato

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ReservationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.reservation_type = ContentType.objects.get_for_model(Reservation)
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
        cls.workplace.volunteers.set([cls.user])
        cls.workplace.save()
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
        cls.reservation_volunteer = Reservation.objects.create(
            user=cls.user,
            timeslot=cls.time_slot,
            is_active=True,
        )
        cls.reservation_admin = Reservation.objects.create(
            user=cls.admin,
            timeslot=cls.time_slot_active,
            is_active=True,
        )

        cls.maxDiff = 5000

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
        del response_data['user_details']
        del response_data['timeslot_details']
        del response_data['id']
        del response_data['url']

        content = {
            'is_active': True,
            'is_present': False,
            'timeslot': f'http://testserver/time_slots/{self.time_slot.id}',
            'user': f'http://testserver/users/{self.user.id}',
            'cancelation_date': None,
            'cancelation_reason': None,
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

        del response_data['timeslot_details']
        del response_data['user_details']
        del response_data['id']
        del response_data['url']

        content = {
            'is_active': True,
            'is_present': False,
            'timeslot': f'http://testserver/time_slots/'
            f'{self.time_slot_active.id}',
            'user': f'http://testserver/users/{self.user.id}',
            'cancelation_date': None,
            'cancelation_reason': None,
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
            'is_active': ['Must be a valid boolean.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can't update a reservation.
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
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_partial(self):
        """
        Ensure we can partially update a reservation (is_present field only).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['timeslot_details']

        content = {
            'id': self.reservation.id,
            'is_active': True,
            'is_present': True,
            'timeslot': f'http://testserver/time_slots/'
            f'{self.time_slot_active.id}',
            'url': f'http://testserver/reservations/{self.reservation.id}',
            'user': f'http://testserver/users/{self.user.id}',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            True,
            Tomato.objects.filter(
                user=self.reservation.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_cancel(self):
        """
        Ensure tomatoes are deleted if we updated with is_present to False
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            True,
            Tomato.objects.filter(
                user=self.reservation.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

        data = {
            'is_present': False,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            False,
            Tomato.objects.filter(
                user=self.reservation.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_as_volunteer(self):
        """
        Ensure we can partially update a reservation (is_present field only)
        if request user is in the timeslot's workplace volunteers list.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                kwargs={'pk': self.reservation_volunteer.pk},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['timeslot_details']
        del response_data['user_details']

        content = {
            'id': self.reservation_volunteer.id,
            'is_active': True,
            'is_present': True,
            'timeslot': f'http://testserver/time_slots/{self.time_slot.id}',
            'url': f'http://testserver/reservations/'
            f'{self.reservation_volunteer.id}',
            'user': f'http://testserver/users/{self.user.id}',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)
        self.assertEqual(
            True,
            Tomato.objects.filter(
                user=self.reservation_volunteer.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation_volunteer.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_as_volunteer_not_owned(self):
        """
        Ensure we can partially update any reservation (is_present field only)
        if request user is in the timeslot's workplace volunteers list.
        """
        self.client.force_authenticate(user=self.user)

        reservation_admin = Reservation.objects.create(
            user=self.admin,
            timeslot=self.time_slot,
            is_active=True,
        )

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                kwargs={'pk': reservation_admin.pk},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['timeslot_details']
        del response_data['user_details']

        content = {
            'id': reservation_admin.id,
            'is_active': True,
            'is_present': True,
            'timeslot': f'http://testserver/time_slots/{self.time_slot.id}',
            'url': f'http://testserver/reservations/{reservation_admin.id}',
            'user': f'http://testserver/users/{self.admin.id}',
            'cancelation_date': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)
        self.assertEqual(
            True,
            Tomato.objects.filter(
                user=reservation_admin.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=reservation_admin.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_as_volunteer_not_active(self):
        """
        Ensure we can't partially update a reservation (is_present field only)
        if is_active == False.
        """
        self.client.force_authenticate(user=self.user)

        reservation_admin = Reservation.objects.create(
            user=self.admin,
            timeslot=self.time_slot,
            is_active=False,
        )

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                kwargs={'pk': reservation_admin.pk},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            response.content
        )
        self.assertEqual(
            False,
            Tomato.objects.filter(
                user=reservation_admin.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=reservation_admin.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_not_volunteer(self):
        """
        Ensure we can't partially update a reservation (is_present field only)
        if request user is not in the timeslot's workplace volunteers list.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            response.content
        )

        self.assertEqual(response_data, content)
        self.assertEqual(
            False,
            Tomato.objects.filter(
                user=self.reservation.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_not_volunteer_not_owned(self):
        """
        Ensure we can't partially update a reservation (is_present field only)
        if request user is not in the timeslot's workplace volunteers list.
        """
        self.client.force_authenticate(user=self.user)

        reservation_admin = Reservation.objects.create(
            user=self.admin,
            timeslot=self.time_slot,
            is_active=False,
        )

        data = {
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                kwargs={'pk': reservation_admin.pk},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            response.content
        )
        self.assertEqual(
            False,
            Tomato.objects.filter(
                user=reservation_admin.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=reservation_admin.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

    def test_update_partial_without_is_present(self):
        """
        Ensure we can't partially update a reservation (other fields).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_active': False,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'is_present': [
                "Only is_present can be updated. To change other "
                "fields, delete this reservation and create a new "
                "one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_with_forbidden_fields(self):
        """
        Ensure we can't partially update a reservation (other fields).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_active': False,
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'is_present': [
                "Only is_present can be updated. To change other "
                "fields, delete this reservation and create a new "
                "one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            False,
            Tomato.objects.filter(
                user=self.reservation.user,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=self.reservation_type,
                object_id=self.reservation.id,
                number_of_tomato=self.reservation.timeslot.number_of_tomatoes
            ).exists())

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
        del data['results'][2]['user_details']
        del data['results'][2]['timeslot_details']

        content = {
            'count': 3,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.reservation.id,
                'is_active': True,
                'is_present': False,
                'timeslot': f'http://testserver/time_slots/'
                f'{self.time_slot_active.id}',
                'url': f'http://testserver/reservations/{self.reservation.id}',
                'user': f'http://testserver/users/{self.user.id}',
                'cancelation_date': None,
                'cancelation_reason': None
            }, {
                'id': self.reservation_volunteer.id,
                'is_active': True,
                'is_present': False,
                'timeslot': f'http://testserver/time_slots/'
                f'{self.time_slot.id}',
                'url': f'http://testserver/reservations/'
                f'{self.reservation_volunteer.id}',
                'user': f'http://testserver/users/{self.user.id}',
                'cancelation_date': None,
                'cancelation_reason': None
            }, {
                'id': self.reservation_admin.id,
                'is_active': True,
                'is_present': False,
                'timeslot': f'http://testserver/time_slots/'
                f'{self.time_slot_active.id}',
                'url': f'http://testserver/reservations/'
                f'{self.reservation_admin.id}',
                'user': f'http://testserver/users/{self.admin.id}',
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

        del data['results'][0]['timeslot_details']
        del data['results'][1]['timeslot_details']
        del data['results'][1]['user_details']

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.reservation.id,
                'is_active': True,
                'is_present': False,
                'timeslot': f'http://testserver/time_slots/'
                f'{self.time_slot_active.id}',
                'url': f'http://testserver/reservations/{self.reservation.id}',
                'user': f'http://testserver/users/{self.user.id}',
                'cancelation_date': None,
                'cancelation_reason': None
            }, {
                'id': self.reservation_volunteer.id,
                'is_active': True,
                'is_present': False,
                'timeslot': f'http://testserver/time_slots/'
                f'{self.time_slot.id}',
                'url': f'http://testserver/reservations/'
                f'{self.reservation_volunteer.id}',
                'user': f'http://testserver/users/{self.user.id}',
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
                args=[self.reservation.id]
            ),
        )

        response_data = json.loads(response.content)

        del response_data['timeslot_details']

        content = {
            'id': self.reservation.id,
            'is_active': True,
            'is_present': False,
            'timeslot': f'http://testserver/time_slots/'
            f'{self.time_slot_active.id}',
            'url': f'http://testserver/reservations/{self.reservation.id}',
            'user': f'http://testserver/users/{self.user.id}',
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
                kwargs={'pk': 3},
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
                    args=[self.reservation.id]
                ),
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

    def test_delete_as_admin(self):
        """
        Ensure that an admin can delete any reservations. Here we don't
        refund the ticket
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    args=[self.reservation.id]
                ),
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_ADMIN_CANCELLED
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.user.ticket = 0

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
                    args=[self.reservation.id]
                ),
            )

        response = self.client.delete(
            reverse(
                'reservation-detail',
                args=[self.reservation.id]
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

    def test_delete_admin_ticket_return(self):
        """
        Ensure that an admin can delete a reservation and return the ticket
        to the user.
        """
        self.client.force_authenticate(user=self.admin)
        user1 = UserFactory(tickets=1)
        reservation1 = Reservation.objects.create(
            user=user1,
            timeslot=self.time_slot_active,
            is_active=True,
        )
        self.assertEqual(user1.tickets, 1)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    args=[reservation1.id]),
                data={'ticket_return': True}
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        modified_user = User.objects.get(id=user1.id)  # reload user
        self.assertEqual(modified_user.tickets, 2)

    def test_delete_admin_own_ticket_return(self):
        """
        Ensure that an admin can delete its own reservation and return the
        ticket to himself.
        """
        self.client.force_authenticate(user=self.admin)
        admin1 = AdminFactory(tickets=1)
        reservation1 = Reservation.objects.create(
            user=admin1,
            timeslot=self.time_slot_active,
            is_active=True,
        )
        self.assertEqual(admin1.tickets, 1)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    args=[reservation1.id]),
                data={'ticket_return': True}
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        modified_admin = User.objects.get(id=admin1.id)  # reload user
        self.assertEqual(modified_admin.tickets, 2)

    def test_delete_admin_ticket_return_null(self):
        """
        Ensure that an admin can delete a reservation and return the ticket
        to the user even if the value of user ticket is null
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory(first_name="Test", tickets=None)
        reservation = Reservation.objects.create(
            user=user,
            timeslot=self.time_slot_active,
            is_active=True,
        )
        self.assertEqual(user.tickets, None)

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'workplace.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'reservation-detail',
                    args=[reservation.id]),
                data={'ticket_return': True}
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        modified_user = User.objects.get(id=user.id)  # reload user
        self.assertEqual(modified_user.tickets, 1)
