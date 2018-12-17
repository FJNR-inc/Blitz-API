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
from blitz_api.services import remove_translation_fields

from ..models import Retirement

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetirementTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(RetirementTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
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
        )

    def test_create(self):
        """
        Ensure we can create a retirement if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_retirement",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'id': 2,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_retirement',
            'next_user_notified': 0,
            'notification_interval': '1 00:00:00',
            'pictures': [],
            'start_time': '2130-01-15T12:00:00-05:00',
            'end_time': '2130-01-17T16:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'activity_language': None,
            'price': '100.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': True,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'url': 'http://testserver/retirement/retirements/2'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid_refund_rate(self):
        """
        Ensure we can't create a retirement if refund_rate is not between
        0 and 100%.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_retirement",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 500,
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {
            'refund_rate': [
                'Refund rate must be between 0 and 100 (%).'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_without_permission(self):
        """
        Ensure we can't create a retirement if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_retirement",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal"
        }

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_duplicate_name(self):
        """
        Ensure we can't create a retirement with same name.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "mega_retirement",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {'name': ['This field must be unique.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a retirement when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {
            'details': ['This field is required.'],
            'address_line1': ['This field is required.'],
            'city': ['This field is required.'],
            'country': ['This field is required.'],
            'name': ['This field is required.'],
            'postal_code': ['This field is required.'],
            'seats': ['This field is required.'],
            'state_province': ['This field is required.'],
            'timezone': ['This field is required.'],
            "price": ["This field is required."],
            "start_time": ["This field is required."],
            "end_time": ["This field is required."],
            "min_day_refund": ["This field is required."],
            "refund_rate": ["This field is required."],
            "min_day_exchange": ["This field is required."],
            "is_active": ["This field is required."]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a retirement with invalid fields.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': ("invalid",),
            'seats': "invalid",
            'activity_language': (1,),
            'details': ("invalid",),
            'postal_code': (1,),
            'city': (1,),
            'address_line1': (1,),
            'country': (1,),
            'state_province': (1,),
            'timezone': ("invalid",),
            'price': "",
            'start_time': "",
            'end_time': "",
            'is_active': "",
            'min_day_exchange': (1,),
            'min_day_refund': (1,),
            'refund_rate': (1,),
        }

        response = self.client.post(
            reverse('retirement:retirement-list'),
            data,
            format='json',
        )

        content = {
            'activity_language': ['"[1]" is not a valid choice.'],
            'details': ['Not a valid string.'],
            'name': ['Not a valid string.'],
            'city': ['Not a valid string.'],
            'address_line1': ['Not a valid string.'],
            'postal_code': ['Not a valid string.'],
            'state_province': ['Not a valid string.'],
            'country': ['Not a valid string.'],
            'seats': ['A valid integer is required.'],
            'timezone': ['Unknown timezone'],
            'is_active': ['"" is not a valid boolean.'],
            'end_time': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'price': ['A valid number is required.'],
            'start_time': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'min_day_exchange': ['A valid integer is required.'],
            'min_day_refund': ['A valid integer is required.'],
            'refund_rate': ['A valid integer is required.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a retirement.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "New Name",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'New city',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'timezone': "America/Montreal",
            'price': '199.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': False,
        }

        response = self.client.put(
            reverse(
                'retirement:retirement-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'activity_language': 'FR',
            'id': 1,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'New city',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'New Name',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'next_user_notified': 0,
            'notification_interval': '1 00:00:00',
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': False,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'url': 'http://testserver/retirement/retirements/1'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a retirement.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retirement:retirement-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list retirements as an unauthenticated user.
        """

        response = self.client.get(
            reverse('retirement:retirement-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'activity_language': 'FR',
                'details': 'This is a description of the mega retirement.',
                'email_content': None,
                'id': 1,
                'address_line1': '123 random street',
                'address_line2': None,
                'city': '',
                'country': 'Random country',
                'postal_code': '123 456',
                'state_province': 'Random state',
                'latitude': None,
                'longitude': None,
                'name': 'mega_retirement',
                'pictures': [],
                'start_time': '2130-01-15T08:00:00-05:00',
                'end_time': '2130-01-17T12:00:00-05:00',
                'seats': 400,
                'reserved_seats': 0,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '199.00',
                'exclusive_memberships': [],
                'timezone': None,
                'is_active': True,
                'places_remaining': 400,
                'min_day_exchange': 7,
                'min_day_refund': 7,
                'refund_rate': 50,
                'reservations': [],
                'reservations_canceled': [],
                'total_reservations': 0,
                'users': [],
                'url': 'http://testserver/retirement/retirements/1'}]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a retirement as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'retirement:retirement-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'details': 'This is a description of the mega retirement.',
            'email_content': None,
            'activity_language': 'FR',
            'id': 1,
            'address_line1': '123 random street',
            'address_line2': None,
            'city': '',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'mega_retirement',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'seats': 400,
            'reserved_seats': 0,
            'next_user_notified': 0,
            'notification_interval': '1 00:00:00',
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': None,
            'is_active': True,
            'places_remaining': 400,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'url': 'http://testserver/retirement/retirements/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_as_admin(self):
        """
        Ensure we can read a retirement as an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retirement:retirement-detail',
                kwargs={'pk': 1},
            ),
        )

        response_data = json.loads(response.content)

        self.assertTrue('name_fr' in response_data)

        response_data = remove_translation_fields(response_data)

        content = {
            'details': 'This is a description of the mega retirement.',
            'activity_language': 'FR',
            'email_content': None,
            'id': 1,
            'address_line1': '123 random street',
            'address_line2': None,
            'city': '',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'mega_retirement',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'reserved_seats': 0,
            'next_user_notified': 0,
            'notification_interval': '1 00:00:00',
            'seats': 400,
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': None,
            'is_active': True,
            'places_remaining': 400,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'url': 'http://testserver/retirement/retirements/1'
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent_retirement(self):
        """
        Ensure we get not found when asking for a retirement that doesn't
        exist.
        """

        response = self.client.get(
            reverse(
                'retirement:retirement-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
